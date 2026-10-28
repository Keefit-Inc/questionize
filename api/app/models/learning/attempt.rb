module Learning
  class Attempt < ApplicationRecord
    belongs_to :user
    belongs_to :item
    belongs_to :item_version

    validates :chosen_label, inclusion: { in: ItemVersion::LABELS }
    validates :skill, presence: true
  end
end
