module Research
  class MemoryLedgerExport
    QUALIFICATION = { "id" => "e11-private-local-pilot", "summary" => "Fresh paired local inference on a source-keyed pilot benchmark. Repeated passes are correlated; this is not an untouched holdout, human explanation audit or learner-growth measurement.",
      "report_url" => "https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E11-upload-driven-memory.md" }.freeze

    def self.entry(cycle)
      cycle.ledger_entry.presence || build_entry(cycle)
    end

    def self.build_entry(cycle)
      first = Array(cycle.evaluation["rounds"]).find { _1["round"] == 1 }
      return unless first && first["n"].to_i >= 12

      n = first["n"]
      summary = %w[baseline candidate].to_h do |condition|
        correct = first["#{condition}_correct"]
        [ condition, { "n" => n, "correct" => correct, "accuracy" => correct.fdiv(n), "calls" => n } ]
      end
      { "run_id" => "memory-cycle-#{cycle.public_id}", "protocol" => "E11", "protocol_version" => 1,
        "capabilities" => [ "C3.1" ], "subject" => "CR", "level" => "gmat", "evaluation_scope" => "trial",
        "started_at" => cycle.created_at.iso8601(6), "git_sha" => cycle.registration["source_revision"],
        "prompts_hash" => cycle.registration["worker_source_hash"], "models" => { "solver" => cycle.registration["model"] || "unrecorded" },
        "judge" => { "version" => "local-fresh-paired-inference-v1" }, "dataset_id" => "private-local-e11-validation",
        "dataset_hash" => Research.digest(cycle.registration.slice("dataset_hash", "validation_hash")),
        "n_items" => n, "split" => "private_local_validation", "baseline_run" => nil,
        "memory" => { "hash" => cycle.candidate.content_hash, "lessons" => cycle.candidate.payload.values.sum(&:size) },
        "note" => "#{cycle.status}: first-pass solving scores; the second fresh pass is a separate reproducibility gate. #{cycle.decision_reasons.join(' ')}",
        "summary" => summary, "qualifications" => [ QUALIFICATION ], "cycle_status" => cycle.status }
    end

    def self.run_data(cycle)
      row = entry(cycle)
      row.except("summary", "level", "evaluation_scope", "cycle_status").merge("scope" => "trial", "measured_capabilities" => [ "C3.1" ])
    end

    def self.records(cycle)
      row = entry(cycle)
      row["summary"].map do |condition, value|
        { "run_id" => row["run_id"], "capability" => "C3.1", "subject" => "CR", "condition" => condition,
          "scope" => "trial", "metric" => "accuracy", "value" => value["accuracy"], "n" => value["n"], "ci95" => nil,
          "expected_n" => row["n_items"], "complete" => true, "calls" => value["calls"] }
      end
    end
  end
end
