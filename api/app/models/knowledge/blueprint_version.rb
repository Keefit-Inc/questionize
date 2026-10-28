module Knowledge
  class BlueprintVersion < ApplicationRecord
    REQUIRED_SPEC_KEYS = %w[objective stimulus_spec key_rule distractor_slots].freeze

    belongs_to :blueprint, class_name: "Knowledge::Blueprint"
    has_many :item_versions, dependent: :nullify

    validates :version, presence: true, uniqueness: { scope: :blueprint_id }
    validates :level_min, :level_max, inclusion: { in: Knowledge::Competency::LEVELS }
    validate :spec_has_required_keys

    private

    def spec_has_required_keys
      missing = REQUIRED_SPEC_KEYS - (spec || {}).keys
      errors.add(:spec, "is missing #{missing.join(', ')}") if missing.any?
    end
  end
end
