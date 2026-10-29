# JSON for a learner's error-log entry: where the question lives in their own book, the
# diagnosis in our words, and new practice items (hidden until answered, like any item).
class ErrorLogPayload
  def initialize(entry, user:)
    @entry = entry
    @user = user
  end

  def as_json(*)
    {
      id: @entry.id,
      book: @entry.book, page: @entry.page, number: @entry.number,
      chosen_label: @entry.chosen_label,
      diagnosis: @entry.diagnosis,
      contributed: @entry.source_observation_id.present?,
      archived: @entry.archived_at.present?,
      dataset: @entry.dataset,
      practice: @entry.practice_items.map { |item| ItemPayload.for(item, user: @user).as_json },
      created_at: @entry.created_at
    }
  end

  # Which traps and misconceptions keep catching this learner.
  def self.weaknesses(entries)
    diagnoses = entries.map(&:diagnosis).reject { _1["chosen_correct"] }
    {
      traps: diagnoses.filter_map { _1["chosen_trap"] }.tally.sort_by { -_2 }.to_h,
      misconceptions: diagnoses.filter_map { _1.dig("misconception", "mechanism_type") }.tally.sort_by { -_2 }.to_h
    }
  end
end
