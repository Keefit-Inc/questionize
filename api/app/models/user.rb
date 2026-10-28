class User < ApplicationRecord
  has_secure_token :api_token
  has_many :skill_ratings, class_name: "Learning::SkillRating", dependent: :destroy
  has_many :attempts, class_name: "Learning::Attempt", dependent: :destroy
  has_many :error_log_entries, class_name: "Learning::ErrorLogEntry", dependent: :destroy
  has_many :saved_items, class_name: "Learning::SavedItem", dependent: :destroy
  has_many :identities, class_name: "UserIdentity", dependent: :destroy
  has_many :feedbacks, dependent: :destroy
  has_many :challenge_answers, class_name: "Learning::ChallengeAnswer", dependent: :destroy
  has_many :generation_runs, dependent: :destroy

  # Countries where photo capture (the error log) is available at launch.
  ERROR_LOG_COUNTRIES = %w[US].freeze

  validates :handle, presence: true, uniqueness: true
  validates :email, uniqueness: true, allow_nil: true
  validates :level, inclusion: { in: Level::ALL }, allow_nil: true

  before_validation :assign_handle, on: :create

  def rating_for(skill)
    skill_ratings.find_or_create_by!(skill: skill)
  end

  def error_log_eligible?
    ERROR_LOG_COUNTRIES.include?(country_code) && age_confirmed_at.present?
  end

  private

  def assign_handle
    self.handle ||= "reader-#{SecureRandom.alphanumeric(8).downcase}"
  end
end
