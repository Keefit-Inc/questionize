class GenerationRun < ApplicationRecord
  STATUSES = %w[queued running completed declined failed].freeze
  KINDS = %w[questions map].freeze
  TEXT_TTL = 1.hour

  belongs_to :user, optional: true
  belongs_to :source, optional: true
  has_many :items, dependent: :nullify
  has_many :challenge_answers, class_name: "Learning::ChallengeAnswer", dependent: :destroy

  validates :status, inclusion: { in: STATUSES }
  validates :kind, inclusion: { in: KINDS }

  scope :completed_maps, -> { where(kind: "map", status: "completed").where.not(result: nil) }

  # Article text lives only in the cache, never in a permanent table.
  def text_cache_key
    "generation_runs/#{id}/text"
  end

  def cache_text!(text)
    Rails.cache.write(text_cache_key, text, expires_in: TEXT_TTL)
  end
end
