module Research
  class DecisionGate
    def self.reasons(cycle, result)
      reasons = []
      baseline = result["baseline"].to_h
      candidate = result["candidate"].to_h
      comparison = result["comparison"].to_h
      n = cycle.benchmark.cases.size
      reasons << "Only recorded-decision replay is supported." unless result["evaluation_kind"] == "decision_replay" && result["evidence_scope"] == "development_regression"
      reasons << "The evaluator did not verify the frozen benchmark hash." unless result["benchmark_hash"] == cycle.benchmark.content_hash
      reasons << "The regression gate did not pass." unless result.dig("gate", "passed") == true
      reasons << "The candidate policy is unchanged." if cycle.candidate_policy.content_hash == cycle.baseline_policy.content_hash
      reasons << "A complete paired sample is required." unless n >= cycle.criteria["min_cases"] && baseline["n"] == n && candidate["n"] == n
      reasons << "At least one EXCEPT decision must improve." unless comparison["except_gained"].to_i >= 1 && comparison["gained"].to_i >= cycle.criteria["min_improvements"]
      reasons << "Correctness regressions are not allowed." unless comparison["lost"] == 0
      reasons << "Standard decisions must remain unchanged." unless comparison["standard_changes"] == 0 && comparison["standard_regressions"] == 0
      if [ baseline, candidate ].all? { _1["correct"].is_a?(Integer) && _1["correct"].between?(0, n) } && n.positive?
        delta = (candidate["correct"] - baseline["correct"]).fdiv(n)
        reasons << "Net accuracy must improve." unless delta.positive?
        reasons << "The recorded difference is inconsistent." unless comparison["delta"].is_a?(Numeric) && (comparison["delta"] - delta).abs < 0.0001
        reasons << "The paired gain/loss counts are inconsistent." unless comparison["gained"].is_a?(Integer) && comparison["lost"].is_a?(Integer) && comparison["gained"] - comparison["lost"] == candidate["correct"] - baseline["correct"]
        [ baseline, candidate ].each do |score|
          reasons << "Accuracy does not match the correct count." unless score["accuracy"].is_a?(Numeric) && (score["accuracy"] - score["correct"].fdiv(n)).abs < 0.0001
        end
      else
        reasons << "Valid correct counts are required."
      end
      reasons.uniq
    end
  end
end
