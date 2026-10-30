module Research
  class PolicyVersion < ApplicationRecord
    validates :public_id, presence: true, uniqueness: true
    validates :version, numericality: { only_integer: true, greater_than: 0 }, uniqueness: { scope: %i[subject level capability] }
    validates :subject, inclusion: { in: [ "CR" ] }
    validates :level, inclusion: { in: [ "gmat" ] }
    validates :capability, inclusion: { in: [ "C3.1" ] }
    validates :kind, inclusion: { in: [ "judge_operator" ] }
    validate :valid_payload
    validate :immutable_version, on: :update

    before_validation :identify, on: :create

    def context
      { "id" => public_id, "hash" => content_hash, "payload" => payload }
    end

    def public_data
      { id: public_id, version: version, content_hash: content_hash, payload: payload }
    end

    private

    def identify
      self.public_id ||= SecureRandom.hex(8)
      self.content_hash ||= Research.digest(payload)
    end

    def valid_payload
      unless payload.is_a?(Hash) && payload.keys == [ "except_mode" ] && %w[legacy abstain].include?(payload["except_mode"])
        errors.add(:payload, "must be the bounded EXCEPT policy")
      end
      errors.add(:content_hash, "does not match payload") unless content_hash == Research.digest(payload)
    end

    def immutable_version
      errors.add(:base, "policy versions are immutable") if changes_to_save.except("updated_at").any?
    end
  end
end
