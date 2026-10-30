module Research
  class MemoryRelease < ApplicationRecord
    belongs_to :memory_version

    def self.current
      first
    end

    def self.bootstrap!
      transaction do
        connection.execute("SELECT pg_advisory_xact_lock(52817921)")
        return first if exists?

        base = MemoryVersion.create!(version: 1, payload: { "expert_rules" => [], "experience_rules" => [] }, provenance: { "kind" => "empty_baseline" })
        create!(memory_version: base, activated_at: Time.current)
      end
    end

    def public_data
      memory_version.public_data.merge(generation: generation, activated_at: activated_at)
    end
  end
end
