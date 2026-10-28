module Learning
  class ChoiceTally < ApplicationRecord
    belongs_to :item_version

    validates :label, inclusion: { in: ItemVersion::LABELS }

    # Atomic increment; safe when many learners answer at once.
    def self.increment!(item_version, label)
      upsert_all(
        [ { item_version_id: item_version.id, label: label, count: 1 } ],
        unique_by: %i[item_version_id label],
        on_duplicate: Arel.sql("count = choice_tallies.count + 1, updated_at = CURRENT_TIMESTAMP")
      )
    end
  end
end
