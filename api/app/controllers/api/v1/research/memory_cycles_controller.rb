class Api::V1::Research::MemoryCyclesController < Api::V1::BaseController
  def show
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Authorization"
    return render(json: { error: "curator_required" }, status: :forbidden) unless current_user.curator

    cycle = ::Research::MemoryCycle.find_by!(public_id: params[:id])
    render json: { id: cycle.public_id, baseline_payload: cycle.baseline.payload, candidate_payload: cycle.candidate&.payload,
      abstract_evidence: ::Research::UploadObservation.where(id: cycle.observation_ids).map { _1.abstract_evidence },
      source_storage: "Original questions and expert explanations are local-only and are not available through this endpoint." }
  end
end
