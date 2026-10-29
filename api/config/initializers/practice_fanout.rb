# Levels that get a practice question written from every snapped question's abstract design, in
# addition to the learner's own level (docs/LEARNING_MODEL.md §4). Off by default: designs are
# learned first and generated from once corroborated (docs/DECISIONS.md R3). Each level costs a
# full writing and verification pass on the AI service.
Rails.application.configure do
  levels = ENV.fetch("PRACTICE_FANOUT_LEVELS", "").split(",").map(&:strip)
  config.x.practice_fanout_levels = levels.reject(&:empty?) # unknown names are ignored where it is used
end
