# Learner levels, matching ai/questionize/levels.py. Grade bands follow US school grades; the
# test-prep levels follow each test's official question types (docs/LEARNING_MODEL.md §4).
module Level
  ALL = %w[elementary middle high college gmat lsat gre].freeze
  DEFAULT = "gmat"

  def self.valid?(level) = ALL.include?(level.to_s)

  def self.for(user) = valid?(user&.level) ? user.level : DEFAULT
end
