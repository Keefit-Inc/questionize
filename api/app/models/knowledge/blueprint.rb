module Knowledge
  class Blueprint < ApplicationRecord
    include Node

    belongs_to :competency, class_name: "Knowledge::Competency", optional: true
    belongs_to :current_version, class_name: "Knowledge::BlueprintVersion", optional: true
    has_many :versions, -> { order(:version) }, class_name: "Knowledge::BlueprintVersion", dependent: :destroy

    # Every change is a new version; items keep pointing at the version they came from.
    def revise!(spec:, level_min:, level_max:, change_note:)
      transaction do
        next_version = (versions.maximum(:version) || 0) + 1
        version = versions.create!(version: next_version, spec: spec, level_min: level_min, level_max: level_max, change_note: change_note)
        update!(current_version: version)
        version
      end
    end
  end
end
