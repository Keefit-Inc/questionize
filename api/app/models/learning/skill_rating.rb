module Learning
  class SkillRating < ApplicationRecord
    belongs_to :user

    validates :skill, presence: true, uniqueness: { scope: :user_id }
  end
end
