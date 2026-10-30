module Research
  class CycleEvent < ApplicationRecord
    belongs_to :cycle
    validates :stage, :message, presence: true
  end
end
