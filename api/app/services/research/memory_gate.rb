module Research
  class MemoryGate
    def self.evaluate(registration, proofs)
      reasons = []
      n = registration["n_items"]
      repeats = registration["repeats"]
      reasons << "At least twelve distinct source-keyed validation items are required." unless n.is_a?(Integer) && n >= 12 && n <= 80
      reasons << "Two fresh paired passes are required." unless repeats == 2
      return { "passed" => false, "reasons" => reasons } if reasons.any?

      reasons << "The paired evaluation is incomplete." unless proofs.is_a?(Array) && proofs.size == n * 2
      return { "passed" => false, "reasons" => reasons } if reasons.any?

      allowed = %w[case_hash round baseline_correct candidate_correct]
      invalid = proofs.any? { |p| !p.is_a?(Hash) || p.keys.sort != allowed.sort || !p["case_hash"].to_s.match?(/\A[0-9a-f]{64}\z/) || ![ 1, 2 ].include?(p["round"]) || ![ true, false ].include?(p["baseline_correct"]) || ![ true, false ].include?(p["candidate_correct"]) }
      return { "passed" => false, "reasons" => [ "Only complete, boolean paired correctness proofs are accepted." ] } if invalid

      rounds = [ 1, 2 ].map do |round|
        rows = proofs.select { _1["round"] == round }
        reasons << "Validation membership must be unique and complete in each pass." unless rows.size == n && rows.map { _1["case_hash"] }.uniq.size == n
        { "round" => round, "n" => rows.size, "baseline_correct" => rows.count { _1["baseline_correct"] },
          "candidate_correct" => rows.count { _1["candidate_correct"] },
          "gained" => rows.count { !_1["baseline_correct"] && _1["candidate_correct"] },
          "lost" => rows.count { _1["baseline_correct"] && !_1["candidate_correct"] } }
      end
      ids = [ 1, 2 ].map { |round| proofs.select { _1["round"] == round }.map { _1["case_hash"] }.sort }
      reasons << "The same validation membership must be used in both passes." unless ids[0] == ids[1]
      reasons << "No correctness regression is allowed." if rounds.any? { _1["lost"].positive? }
      gained = [ 1, 2 ].map { |round| proofs.select { _1["round"] == round && !_1["baseline_correct"] && _1["candidate_correct"] }.map { _1["case_hash"] } }
      stable = gained[0] & gained[1]
      reasons << "No improvement was reproduced on the same validation item in both passes." if stable.empty?
      { "passed" => reasons.empty?, "reasons" => reasons.uniq, "rounds" => rounds, "stable_gains" => stable.size,
        "evaluation_kind" => "fresh_paired_inference", "executor" => "private_local_worker",
        "n_items" => n, "repeats" => repeats, "interpretation" => "Local source-keyed pilot; repeated passes are correlated, not proof of population or learner gains." }
    end
  end
end
