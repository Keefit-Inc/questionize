module Knowledge
  class CompetencyMisconception < ApplicationRecord
    belongs_to :competency, class_name: "Knowledge::Competency"
    belongs_to :misconception, class_name: "Knowledge::Misconception"
  end
end
