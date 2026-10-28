class GenerationRun < ApplicationRecord
  STATUSES = %w[queued running completed declined failed].freeze
  TEXT_TTL = 1.hour

  belongs_to :user, optional: true
  belongs_to :source, optional: true
  has_many :items, dependent: :nullify

  validates :status, inclusion: { in: STATUSES }

  # Article text lives only in the cache, never in a permanent table.
  def text_cache_key
    "generation_runs/#{id}/text"
  end

  def cache_text!(text)
    Rails.cache.write(text_cache_key, text, expires_in: TEXT_TTL)
  end
end
