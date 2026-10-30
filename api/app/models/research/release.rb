module Research
  class Release < ApplicationRecord
    belongs_to :policy_version
    has_many :cycles, dependent: :restrict_with_exception
    validates :subject, uniqueness: { scope: %i[level capability] }

    def self.bootstrap!
      transaction do
        existing = find_by(subject: "CR", level: "gmat", capability: "C3.1")
        return existing if existing

        policy = PolicyVersion.create!(version: 1, payload: { "except_mode" => "legacy" },
          provenance: { "kind" => "existing_service_baseline" })
        create!(subject: "CR", level: "gmat", capability: "C3.1", policy_version: policy, activated_at: Time.current)
      end
    rescue ActiveRecord::RecordNotUnique
      find_by!(subject: "CR", level: "gmat", capability: "C3.1")
    end

    def self.context_for(level:, family: "CR")
      return unless level == "gmat" && family == "CR"

      find_by(subject: "CR", level: "gmat", capability: "C3.1")&.policy_version&.context
    end

    def public_data
      policy_version.public_data.merge(activated_at: activated_at, generation: generation,
        cycle_id: cycles.where(status: "adopted", candidate_policy_id: policy_version_id).order(:id).last&.public_id)
    end
  end
end
