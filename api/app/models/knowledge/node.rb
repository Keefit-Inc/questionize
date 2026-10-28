module Knowledge
  # Shared behavior for knowledge nodes: a status lifecycle with an auditable history.
  module Node
    extend ActiveSupport::Concern

    included do
      has_many :status_events, as: :node, class_name: "Knowledge::NodeStatusEvent", dependent: :destroy

      validates :key, presence: true, uniqueness: true
      validates :status, inclusion: { in: Knowledge::STATUSES }
      validates :confidence, numericality: { greater_than_or_equal_to: 0, less_than_or_equal_to: 1 }
    end

    def transition_to!(new_status, reason:, evidence: {})
      transaction do
        status_events.create!(from_status: status, to_status: new_status, reason: reason, evidence: evidence)
        update!(status: new_status)
      end
    end
  end
end
