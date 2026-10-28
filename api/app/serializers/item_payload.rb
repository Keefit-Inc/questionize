# JSON for an item. The key, explanations, trap tags and tallies stay hidden until the
# requesting user has attempted the item (CLAUDE.md rules).
class ItemPayload
  def initialize(item, revealed:)
    @item = item
    @version = item.current_version
    @revealed = revealed
  end

  def self.for(item, user:)
    new(item, revealed: user.present? && Learning::Attempt.exists?(user: user, item: item))
  end

  def as_json(*)
    base = {
      id: @item.public_id,
      family: @item.family,
      subtype: @item.subtype,
      verified: @item.status == "verified",
      status: @item.status,
      version: @version.version,
      passage: @version.passage,
      stem: @version.stem,
      choices: @version.choices,
      skill: @version.skill,
      attempts_count: @item.attempts_count,
      source: source_json,
      revealed: @revealed
    }
    @revealed ? base.merge(reveal) : base
  end

  private

  def reveal
    {
      correct_label: @version.correct_label,
      explanation: @version.explanation,
      rationales: @version.rationales,
      source_anchor: @version.source_anchor,
      tally: @version.tally,
      correct_rate: @item.attempts_count.zero? ? nil : (@item.correct_count.to_f / @item.attempts_count).round(3),
      verification: @version.verification.except("judge"),
      judge: judge_json
    }
  end

  # Argument Judge measurements per option, shown with the explanation.
  def judge_json
    summary = @version.verification["judge"]
    return nil unless summary

    measurements = @version.judge_measurements.where(judge_version: summary["judge_version"]).group_by(&:label)
    options = ItemVersion::LABELS.map do |label|
      values = measurements.fetch(label, []).index_by(&:measure)
      { label: label }.merge(values.transform_values { |m| { value: m.value, ci_low: m.ci_low, ci_high: m.ci_high } })
    end
    summary.merge("options" => options)
  end

  def source_json
    return nil unless @item.source

    { title: @item.source.title, domain: @item.source.domain, url: @item.source.canonical_url }
  end
end
