namespace :questionize do
  desc "Temporarily label an existing dedicated test device so its uploads never count as learner traction"
  task mark_operator_device: :environment do
    input = JSON.parse($stdin.read)
    user = User.find(input.fetch("user_id"))
    Rails.cache.write("research/operator-test-user/#{user.id}", true, expires_in: 2.hours)
    puts({ operator_test: true, user_id: user.id }.to_json)
  end
  desc "Initialize the empty, immutable GMAT CR solving memory"
  task memory_bootstrap: :environment do
    puts Research::MemoryRelease.bootstrap!.public_data.to_json
  end

  desc "Register a scoped local-worker credential digest from stdin (never send its plaintext token)"
  task worker_register: :environment do
    input = JSON.parse($stdin.read)
    digest = input.fetch("token_digest")
    abort "Invalid digest" unless digest.match?(/\A[0-9a-f]{64}\z/)
    worker = Research::WorkerCredential.find_or_create_by!(token_digest: digest) { _1.name = input.fetch("name").to_s.first(100) }
    puts({ registered: true, id: worker.id }.to_json)
  end

  desc "Record an abstract operator audit on stdin; no question, key or explanation fields accepted"
  task upload_audit: :environment do
    input = JSON.parse($stdin.read)
    allowed = %w[question_fingerprint reference_status reference_source knowledge_origin subtype outcome abstract_evidence measurements]
    abort "Unsupported fields" unless (input.keys - allowed).empty?
    release = Research::MemoryRelease.bootstrap!
    applied = input.dig("measurements", "memory_hash") == release.memory_version.content_hash ? release.memory_version_id : nil
    o = Research::UploadObservation.create!(input.merge("memory_version_id" => applied, "operator_test" => true))
    puts({ observation_id: o.public_id, operator_test: true }.to_json)
    Research::UploadScheduleJob.perform_later
  end

  desc "Run an original operator-only image capture through the actual production job; images are transient"
  task upload_probe: :environment do
    input = JSON.parse($stdin.read)
    images = input.fetch("images")
    abort "Invalid images" unless images.is_a?(Array) && images.size.between?(1, 3) && images.all? { _1.start_with?("data:image/") && _1.bytesize < 12.megabytes }
    # A dedicated device, never the operator's mobile account or the public Bank.
    user = User.create!(level: "gmat", curator: true)
    run = GenerationRun.create!(user: user, kind: "error_log", params: { "level" => "gmat", "learn_only" => true,
      "operator_test" => true, "answer_key" => input.fetch("answer_key"), "source_attested" => true, "dataset" => "operator-original-contract" })
    run.cache_text!(images.to_json)
    GenerateQuestionsJob.perform_later(run.id)
    puts({ run_id: run.id, operator_test: true }.to_json)
  end
end
