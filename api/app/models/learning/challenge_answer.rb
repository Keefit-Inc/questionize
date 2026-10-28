module Learning
  class ChallengeAnswer < ApplicationRecord
    belongs_to :user
    belongs_to :generation_run

    validates :challenge_index, numericality: { greater_than_or_equal_to: 0 }
    validates :choice, inclusion: { in: ItemVersion::LABELS }
    validates :challenge_index, uniqueness: { scope: %i[user_id generation_run_id] }
  end
end
