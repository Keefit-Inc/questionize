# Levels that get a practice question written from every snapped question's abstract design, in
# addition to the learner's own level (docs/LEARNING_MODEL.md §4). Each one costs a full writing and
# verification pass on the AI service, so keep the list short.
Rails.application.configure do
  levels = ENV.fetch("PRACTICE_FANOUT_LEVELS", "middle,high,college").split(",").map(&:strip)
  config.x.practice_fanout_levels = levels.reject(&:empty?) # unknown names are ignored where it is used
end
