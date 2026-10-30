module Learning
  class Attempt < ApplicationRecord
    belongs_to :user
    belongs_to :item
    belongs_to :item_version

    validates :chosen_label, inclusion: { in: ItemVersion::LABELS }
    validates :skill, presence: true
    after_create_commit :check_research_batch

    private

    def check_research_batch
      Research::Evidence.request_check if rated && item.family == "CR" && item.level == "gmat"
    end
  end
end
