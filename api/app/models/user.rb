class User < ApplicationRecord
  has_secure_token :api_token
  has_many :skill_ratings, class_name: "Learning::SkillRating", dependent: :destroy
  has_many :attempts, class_name: "Learning::Attempt", dependent: :destroy

  validates :handle, presence: true, uniqueness: true
  validates :email, uniqueness: true, allow_nil: true

  before_validation :assign_handle, on: :create

  def rating_for(skill)
    skill_ratings.find_or_create_by!(skill: skill)
  end

  private

  def assign_handle
    self.handle ||= "reader-#{SecureRandom.alphanumeric(8).downcase}"
  end
end
