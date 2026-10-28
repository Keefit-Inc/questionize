module Learning
  # A bank item on a learner's review list: one they missed on their first try, or saved to
  # practice later. Archiving moves it out of the list without forgetting it.
  class SavedItem < ApplicationRecord
    self.table_name = "saved_items"

    REASONS = %w[missed saved].freeze

    belongs_to :user
    belongs_to :item

    validates :reason, inclusion: { in: REASONS }

    scope :active, -> { where(archived_at: nil) }
    scope :archived, -> { where.not(archived_at: nil) }

    # Adds the item to the list, or brings it back if it was archived. Never downgrades "missed".
    def self.keep!(user:, item:, reason:)
      saved = find_or_initialize_by(user: user, item: item)
      saved.reason = reason if saved.new_record? || reason == "missed"
      saved.archived_at = nil
      saved.save!
      saved
    rescue ActiveRecord::RecordNotUnique
      retry
    end
  end
end
