class GenerationRun < ApplicationRecord
  STATUSES = %w[queued running completed declined failed].freeze
  KINDS = %w[questions map error_log practice].freeze
  TEXT_TTL = 1.hour

  belongs_to :user, optional: true
  belongs_to :source, optional: true
  has_many :items, dependent: :nullify
  has_many :challenge_answers, class_name: "Learning::ChallengeAnswer", dependent: :destroy

  validates :status, inclusion: { in: STATUSES }
  validates :kind, inclusion: { in: KINDS }
  before_validation :pin_capability_policy, on: :create

  scope :completed_maps, -> { where(kind: "map", status: "completed").where.not(result: nil) }

  IMAGE_TTL = 15.minutes

  # The run's input (article text, or for the error log a photo as a data: URL) lives only in
  # the cache, never in a permanent table, and the job deletes it as soon as it is read.
  def text_cache_key
    "generation_runs/#{id}/text"
  end

  def cache_text!(text)
    Rails.cache.write(text_cache_key, text, expires_in: kind == "error_log" ? IMAGE_TTL : TEXT_TTL)
  end

  private

  def pin_capability_policy
    return unless %w[questions error_log practice].include?(kind)

    # The public caller cannot select a research policy. Even a legacy nil context is pinned,
    # so requests already queued when a release changes retain their original semantics.
    self.params = (params || {}).except("capability_policy").merge(
      "capability_policy" => Research::Release.context_for(level: params&.fetch("level", nil) || Level.for(user))
    )
  end
end
