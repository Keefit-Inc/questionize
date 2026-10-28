# JSON for an argument map (docs/ARCHITECTURE.md §5.0). The structure and the judge's view of
# each premise and assumption are shown up front; each challenge's judged answer, its option
# measurements and what other readers chose stay hidden until this user has answered it.
class MapPayload
  def initialize(run, user:)
    @run = run
    @map = run.result || {}
    @answers = user ? Learning::ChallengeAnswer.where(user: user, generation_run: run).pluck(:challenge_index, :choice).to_h : {}
  end

  def as_json(*)
    {
      run_id: @run.id,
      reconstruction: true,
      judge_version: @map["judge_version"],
      scheme: @map["scheme"],
      conclusion: @map["conclusion"],
      premises: @map["premises"],
      assumptions: @map["assumptions"],
      largest_gap: @map["largest_gap"],
      challenges: Array(@map["challenges"]).map { |challenge| challenge_json(challenge) }
    }
  end

  private

  def challenge_json(challenge)
    index = challenge["index"]
    chosen = @answers[index]
    base = {
      index: index, kind: challenge["kind"], question: challenge["question"],
      options: challenge["options"].map { |o| o.slice("label", "text") },
      chosen: chosen, revealed: chosen.present?
    }
    return base unless chosen

    base.merge(
      options: challenge["options"],
      judged: challenge["judged"],
      crowd: crowd(index)
    )
  end

  def crowd(index)
    counts = Learning::ChallengeAnswer.where(generation_run: @run, challenge_index: index).group(:choice).count
    ItemVersion::LABELS.index_with { |label| counts.fetch(label, 0) }
  end
end
