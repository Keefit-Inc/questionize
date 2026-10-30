module Research
  class LedgerExport
    QUALIFICATION = {
      "id" => "e8-development-replay",
      "summary" => "Recorded decision replay on a known development regression set. No new solver inference, untouched holdout or learner-growth measurement.",
      "report_url" => "https://github.com/Keefit-Inc/questionize/blob/main/research/protocols/E8-policy-evolution.md"
    }.freeze

    def self.entry(cycle)
      summary = {}
      %w[baseline candidate].each do |condition|
        result = cycle.evaluation[condition].to_h
        next unless result["accuracy"].is_a?(Numeric)

        summary[condition] = result.slice("n", "correct", "accuracy", "ci95").merge("calls" => 0)
      end
      {
        "run_id" => "cycle-#{cycle.public_id}", "protocol" => "E8", "protocol_version" => 1,
        "capabilities" => [ "C3.1" ], "subject" => "CR", "level" => "gmat", "evaluation_scope" => "regression",
        "started_at" => cycle.created_at.iso8601(6), "git_sha" => cycle.code_revision,
        "prompts_hash" => cycle.proposal["prompt_hash"],
        "models" => { "candidate_generator" => cycle.proposal["model"] || "not_run" },
        "judge" => { "version" => "recorded-decision-replay-v1" },
        "dataset_id" => cycle.benchmark.public_id, "dataset_hash" => cycle.benchmark.content_hash,
        "n_items" => cycle.benchmark.cases.size, "split" => "development_regression", "memory" => nil,
        "baseline_run" => nil, "note" => "#{cycle.status}: #{cycle.decision_reasons.join(' ')}",
        "summary" => summary, "qualifications" => [ QUALIFICATION ],
        "policy_versions" => { "baseline" => cycle.baseline_policy.public_data, "candidate" => cycle.candidate_policy&.public_data },
        "cycle_status" => cycle.status
      }
    end

    def self.run_data(cycle)
      row = cycle.ledger_entry.presence || entry(cycle)
      row.slice("run_id", "protocol", "protocol_version", "started_at", "git_sha", "prompts_hash", "models", "judge", "dataset_id", "dataset_hash", "split", "n_items", "baseline_run", "note", "memory", "qualifications").merge(
        "subject" => "CR", "scope" => "regression", "capabilities" => [ "C3.1" ],
        "measured_capabilities" => row["summary"].present? ? [ "C3.1" ] : []
      )
    end

    def self.records(cycle)
      row = cycle.ledger_entry.presence || entry(cycle)
      row.fetch("summary", {}).map do |condition, value|
        { "run_id" => row["run_id"], "capability" => "C3.1", "subject" => "CR", "condition" => condition,
          "scope" => "regression", "metric" => "accuracy", "value" => value["accuracy"], "n" => value["n"],
          "ci95" => value["ci95"], "expected_n" => row["n_items"], "complete" => value["n"] == row["n_items"], "calls" => 0 }
      end
    end
  end
end
