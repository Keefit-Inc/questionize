module Knowledge
  class TrapPatternTarget < ApplicationRecord
    belongs_to :trap_pattern, class_name: "Knowledge::TrapPattern"
    belongs_to :misconception, class_name: "Knowledge::Misconception"
  end
end
