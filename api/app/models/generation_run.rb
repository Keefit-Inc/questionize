class GenerationRun < ApplicationRecord
  STATUSES = %w[queued running completed declined failed].freeze

  belongs_to :user, optional: true
  belongs_to :source, optional: true
  has_many :items, dependent: :nullify

  validates :status, inclusion: { in: STATUSES }
end
