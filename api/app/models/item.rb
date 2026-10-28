class Item < ApplicationRecord
  FAMILIES = %w[CR RC SC].freeze
  STATUSES = %w[verified unverified flagged under_review retired].freeze
  VISIBILITIES = %w[private public held].freeze
  ORIGINS = %w[generated contributed pattern].freeze
  START_RATINGS = { "easy" => 1300.0, "medium" => 1500.0, "hard" => 1700.0 }.freeze

  belongs_to :source, optional: true
  belongs_to :generation_run, optional: true
  belongs_to :current_version, class_name: "ItemVersion", optional: true
  has_many :versions, -> { order(:version) }, class_name: "ItemVersion", dependent: :destroy
  has_many :attempts, class_name: "Learning::Attempt", dependent: :destroy

  validates :family, inclusion: { in: FAMILIES }
  validates :subtype, presence: true
  validates :status, inclusion: { in: STATUSES }
  validates :visibility, inclusion: { in: VISIBILITIES }
  validates :origin, inclusion: { in: ORIGINS }

  before_validation :assign_public_id, on: :create

  def self.start_rating(difficulty)
    START_RATINGS.fetch(difficulty.to_s, START_RATINGS["medium"])
  end

  # Ratings are kept per sub-type, rolled up to the family and overall.
  def skill
    "#{family}:#{subtype}"
  end

  def skill_chain
    [ skill, family, "overall" ]
  end

  def to_param
    public_id
  end

  private

  def assign_public_id
    self.public_id ||= SecureRandom.alphanumeric(10)
  end
end
