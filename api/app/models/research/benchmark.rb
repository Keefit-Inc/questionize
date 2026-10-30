module Research
  class Benchmark < ApplicationRecord
    CASE_KEYS = %w[case_id subtype operator solver_answer judge_answer judge_first_rate key baseline_answer].freeze
    LABELS = %w[A B C D E].freeze

    validates :public_id, :name, :content_hash, presence: true
    validates :public_id, :content_hash, uniqueness: true
    validates :subject, inclusion: { in: [ "CR" ] }
    validates :level, inclusion: { in: [ "gmat" ] }
    validates :kind, inclusion: { in: [ "decision_replay" ] }
    validates :purpose, inclusion: { in: [ "development_regression" ] }
    validate :safe_cases
    validate :immutable_evidence, on: :update
    before_validation :identify, on: :create

    def context
      { "id" => public_id, "hash" => content_hash, "kind" => kind, "cases" => cases }
    end

    def public_data
      { id: public_id, name: name, hash: content_hash, n: cases.size, kind: kind, purpose: purpose,
        parent_dataset_hash: provenance["parent_dataset_hash"], source_run: provenance["source_run"] }
    end

    private

    def identify
      self.public_id ||= SecureRandom.hex(8)
      self.content_hash ||= Research.digest(cases)
    end

    def safe_cases
      unless cases.is_a?(Array) && cases.size.between?(1, 200)
        return errors.add(:cases, "must contain 1 to 200 abstract decisions")
      end
      valid = cases.all? do |c|
        c.is_a?(Hash) && (c.keys - CASE_KEYS).empty? && c.keys.sort == CASE_KEYS.sort &&
          c["case_id"].to_s.match?(/\A[0-9a-f]{16,64}\z/) && c["subtype"].to_s.match?(/\A[a-z_]{1,40}\z/) &&
          c["subtype"] != "structure" && %w[standard except].include?(c["operator"]) &&
          %w[solver_answer key baseline_answer].all? { LABELS.include?(c[_1]) } &&
          (c["judge_answer"].nil? || LABELS.include?(c["judge_answer"])) &&
          (c["judge_answer"].nil? == c["judge_first_rate"].nil?) &&
          (c["judge_first_rate"].nil? || (c["judge_first_rate"].is_a?(Numeric) && c["judge_first_rate"].between?(0, 1)))
      end
      errors.add(:cases, "contains invalid or non-abstract evidence") unless valid
      errors.add(:cases, "contains duplicate case hashes") unless cases.filter_map { _1["case_id"] if _1.is_a?(Hash) }.uniq.size == cases.size
      errors.add(:content_hash, "does not match frozen cases") unless content_hash == Research.digest(cases)
      if valid
        legacy_matches = cases.all? do |c|
          judged = %w[strengthen weaken assumption].include?(c["subtype"]) && c["judge_answer"] && c["judge_first_rate"].to_f >= 0.8
          (judged ? c["judge_answer"] : c["solver_answer"]) == c["baseline_answer"]
        end
        errors.add(:cases, "does not reproduce the historical legacy policy") unless legacy_matches
      end
    end

    def immutable_evidence
      errors.add(:base, "benchmark evidence is immutable") if changes_to_save.except("enabled", "updated_at").any?
    end
  end
end
