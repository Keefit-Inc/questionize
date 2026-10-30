class Api::V1::Research::WorkerController < ActionController::API
  before_action :authenticate_worker

  def heartbeat
    @worker.update!(last_seen_at: Time.current)
    head :no_content
  end

  def lease
    @worker.update!(last_seen_at: Time.current)
    cycle = ::Research::MemoryCycle.find_by(status: "queued")
    return head :no_content unless cycle

    token = SecureRandom.hex(32)
    cycle.with_lock do
      return head :no_content unless cycle.status == "queued"

      cycle.update!(status: "generating", lease_digest: Digest::SHA256.hexdigest(token), leased_at: Time.current, lease_expires_at: 30.minutes.from_now)
      cycle.event!("worker_leased", "The private local evaluator accepted the abstract observation batch.")
    end
    observations = ::Research::UploadObservation.where(id: cycle.observation_ids)
    render json: { id: cycle.public_id, lease: token, baseline: cycle.baseline.context,
      observations: observations.map { |o| o.public_data.merge(abstract_evidence: o.abstract_evidence, question_fingerprint: o.question_fingerprint) },
      protocol: "E11", protocol_version: 1, min_validation_items: 12, repeats: 2 }
  end

  def candidate
    cycle = leased_cycle
    return unless cycle

    registration = params.require(:registration).permit(:dataset_hash, :validation_hash, :training_hash, :n_items, :repeats,
      :worker_source_hash, :model, :source_revision,
      :validation_label_source, validation_fingerprints: [], training_fingerprints: []).to_h
    registration["n_items"] = registration["n_items"].to_i
    registration["repeats"] = registration["repeats"].to_i
    validation = Array(registration["validation_fingerprints"])
    training = Array(registration["training_fingerprints"])
    sources = ::Research::UploadObservation.where(id: cycle.observation_ids).pluck(:question_fingerprint)
    valid = registration["n_items"].between?(12, 80) && registration["repeats"] == 2 && validation.size == registration["n_items"] && validation.uniq.size == validation.size
    valid &&= (validation + training).all? { _1.to_s.match?(/\A[0-9a-f]{64}\z/) } && (validation & (training + sources)).empty?
    valid &&= registration["validation_hash"] == ::Research.digest(validation.sort) && registration["training_hash"] == ::Research.digest(training.sort)
    valid &&= registration["validation_label_source"] == "source_reference"
    return render(json: { error: "invalid_or_contaminated_validation_registration" }, status: :unprocessable_entity) unless valid

    payload = params.require(:payload).permit(expert_rules: [], experience_rules: []).to_h
    if payload.values.flatten.any? { _1.to_s.match?(/ignore (?:all |previous |system )?instructions|always (?:choose|pick|answer)\s+[A-E]\b|https?:\/\//i) }
      return render json: { error: "unsupported_question_specific_or_instruction_rule" }, status: :unprocessable_entity
    end
    release = ::Research::MemoryRelease.current
    release.with_lock do
      return render(json: { error: "stale_baseline" }, status: :conflict) unless release.memory_version_id == cycle.baseline_id && cycle.status == "generating"

      version = ::Research::MemoryVersion.create!(version: ::Research::MemoryVersion.maximum(:version).to_i + 1,
        parent: cycle.baseline, payload: payload, provenance: { "cycle_id" => cycle.public_id, "protocol" => "E11", "origin" => "local_worker_model_extracted" })
      cycle.update!(candidate: version, registration: cycle.registration.merge(registration).merge("protocol" => "E11", "protocol_version" => 1), status: "evaluating")
      cycle.event!("candidate_registered", "A private bounded candidate and disjoint source-keyed local validation membership were frozen before evaluation.")
    end
    render json: { candidate: cycle.candidate.public_data }
  rescue ActiveRecord::RecordInvalid, ActionController::ParameterMissing
    render json: { error: "invalid_candidate" }, status: :unprocessable_entity
  end

  def report
    cycle = leased_cycle
    return unless cycle
    return render(json: { error: "unexpected_stage" }, status: :conflict) unless cycle.status == "evaluating"
    proofs = Array(params[:proofs]).map { _1.respond_to?(:to_unsafe_h) ? _1.to_unsafe_h : _1 }
    allowed = Array(cycle.registration["validation_fingerprints"])
    result = ::Research::MemoryGate.evaluate(cycle.registration, proofs)
    unless proofs.all? { _1.is_a?(Hash) && allowed.include?(_1["case_hash"]) }
      result = { "passed" => false, "reasons" => [ "Reported validation membership does not match the frozen registration." ] }
    end
    if params[:candidate_hash] != cycle.candidate.content_hash || params[:baseline_hash] != cycle.baseline.content_hash
      result = { "passed" => false, "reasons" => [ "The evaluated policy hashes do not match the frozen versions." ] }
    end
    cycle.update!(evaluation: result.merge("proofs" => proofs))
    if result["passed"] && cycle.candidate.content_hash != cycle.baseline.content_hash
      cycle.update!(status: "activating")
      cycle.event!("evaluation_passed", "The same validation gain was reproduced in two fresh paired passes with no regression.")
      ::Research::MemoryActivateJob.perform_later(cycle.id)
    else
      cycle.finish!("held", decision_reasons: Array(result["reasons"]).presence || [ "No change from the active memory." ])
      advance_cursor(cycle)
      cycle.event!("held", "The candidate did not establish a reproducible improvement; active memory retained.")
    end
    render json: cycle.public_data
  end

  def failure
    cycle = leased_cycle
    return unless cycle

    reason = %w[local_dataset_unavailable insufficient_validation provider_failure no_usable_candidate].include?(params[:reason]) ? params[:reason] : "local_worker_failure"
    return render(json: { error: "unexpected_stage" }, status: :conflict) unless %w[generating evaluating].include?(cycle.status)
    cycle.finish!(reason == "no_usable_candidate" ? "held" : "failed", decision_reasons: [ reason ])
    advance_cursor(cycle) if reason == "no_usable_candidate"
    cycle.event!("failed", "Local evaluation stopped; original material remained local and the active service version was retained.")
    render json: cycle.public_data
  end

  private

  def authenticate_worker
    token = request.authorization.to_s[/\ABearer\s+(.+)\z/i, 1]
    @worker = ::Research::WorkerCredential.authenticate(token)
    head :unauthorized unless @worker
  end

  def leased_cycle
    cycle = ::Research::MemoryCycle.find_by(public_id: params[:id])
    digest = Digest::SHA256.hexdigest(params[:lease].to_s)
    unless cycle && cycle.lease_digest.present? && ActiveSupport::SecurityUtils.secure_compare(cycle.lease_digest, digest) && cycle.lease_expires_at > Time.current
      render json: { error: "invalid_or_expired_lease" }, status: :forbidden
      return
    end
    @worker.update!(last_seen_at: Time.current)
    cycle
  end

  def advance_cursor(cycle)
    release = ::Research::MemoryRelease.current
    release.with_lock { release.update!(observation_cursor: [ release.observation_cursor, cycle.registration["source_to_id"].to_i, cycle.observation_ids.max.to_i ].max) }
  end
end
