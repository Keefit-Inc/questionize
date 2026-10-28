module Knowledge
  class NodeStatusEvent < ApplicationRecord
    belongs_to :node, polymorphic: true

    validates :to_status, inclusion: { in: Knowledge::STATUSES }
    validates :reason, presence: true
  end
end
