# JSON for an item. The key, explanations, trap tags and tallies stay hidden until the
# requesting user has attempted the item (CLAUDE.md rules).
class ItemPayload
  def self.for(item, user:)
    new(item, revealed: user.present? && Learning::Attempt.exists?(user: user, item: item), user: user)
  end

  def initialize(item, revealed:, user: nil)
    @item = item
    @version = item.current_version
    @revealed = revealed
    @user = user
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
      revealed: @revealed,
      origin: @item.origin,
      level: @item.level,
      scene: @item.scene,
      saved: saved_json
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
      judge: judge_json,
      votes: votes_json
    }
  end

  # Whether the item is on this learner's review list, and why.
  def saved_json
    return nil unless @user

    saved = Learning::SavedItem.find_by(user: @user, item: @item)
    saved && { reason: saved.reason, archived: saved.archived_at.present? }
  end

  # Learners rate a question once they've answered it.
  def votes_json
    counts = @version.feedbacks.where(kind: %w[up down]).group(:kind).count
    mine = @user && @version.feedbacks.where(user: @user, kind: %w[up down]).order(:updated_at).last&.kind
    { up: counts.fetch("up", 0), down: counts.fetch("down", 0), mine: mine }
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
