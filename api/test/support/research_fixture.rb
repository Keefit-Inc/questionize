module ResearchFixture
  def replay_cases
    35.times.map do |i|
      { "case_id" => format("%024x", i + 1), "subtype" => "strengthen", "operator" => i == 34 ? "except" : "standard",
        "solver_answer" => "A", "judge_answer" => i == 34 ? "B" : "A", "judge_first_rate" => 1.0,
        "key" => "A", "baseline_answer" => i == 34 ? "B" : "A" }
    end
  end

  def configure_research
    release = Research::Release.bootstrap!
    benchmark = Research::Benchmark.create!(name: "Synthetic integration fixture", cases: replay_cases,
      provenance: { "parent_dataset_hash" => "synthetic", "source_run" => "offline-test" }, enabled: true)
    [ release, benchmark ]
  end

  class PolicyClient
    attr_accessor :mode, :on_evaluate, :fail_after_switch
    attr_reader :probes, :requests

    def initialize(mode: "abstain")
      @mode, @probes, @requests = mode, 0, []
    end

    def propose_policy(payload)
      @requests << payload
      { "payload" => { "except_mode" => mode }, "reason" => "Review the unsupported task operator.",
        "hypothesis" => "Abstention prevents the recorded incorrect override.", "model" => "offline-test",
        "generator_version" => "test-v1", "logical_calls" => 1, "duration_seconds" => 0.01 }
    end

    def evaluate_policy(payload)
      on_evaluate&.call
      @requests << payload
      cases = payload["benchmark"]["cases"]
      decide = lambda do |policy|
        cases.map { |c| policy["payload"]["except_mode"] == "abstain" && c["operator"] == "except" ? c["solver_answer"] : c["judge_answer"] || c["solver_answer"] }
      end
      before, after = decide.call(payload["baseline"]), decide.call(payload["candidate"])
      correct = ->(answers) { answers.zip(cases).count { |answer, c| answer == c["key"] } }
      gained = cases.each_index.count { |i| before[i] != cases[i]["key"] && after[i] == cases[i]["key"] }
      lost = cases.each_index.count { |i| before[i] == cases[i]["key"] && after[i] != cases[i]["key"] }
      changes = cases.each_index.count { |i| cases[i]["operator"] == "standard" && before[i] != after[i] }
      summary = ->(answers) { { "n" => cases.size, "correct" => correct.call(answers), "accuracy" => correct.call(answers).fdiv(cases.size).round(4), "ci95" => [ 0.8, 1.0 ] } }
      {
        "evaluation_kind" => "decision_replay", "evidence_scope" => "development_regression", "benchmark_hash" => payload["benchmark"]["hash"],
        "baseline" => summary.call(before), "candidate" => summary.call(after),
        "comparison" => { "gained" => gained, "lost" => lost, "delta" => (gained - lost).fdiv(cases.size).round(4),
          "mcnemar_p" => 1.0, "diff_ci95" => [ 0.0, 0.08 ], "standard_changes" => changes, "standard_regressions" => 0,
          "except_gained" => gained },
        "gate" => { "passed" => gained.positive? && lost.zero? && changes.zero?, "reasons" => gained.positive? ? [] : [ "no_improvement" ] },
        "proofs" => [ { "private_case" => "never-public" } ]
      }
    end

    def probe_policy(payload)
      @probes += 1
      raise AiService::Error, "offline failure" if fail_after_switch && probes == 2

      @requests << payload
      { "policy_id" => payload["policy"]["id"], "policy_hash" => payload["policy"]["hash"], "chosen_answer" => "A", "applied" => true, "reason" => "unsupported_except_objective" }
    end
  end
end
