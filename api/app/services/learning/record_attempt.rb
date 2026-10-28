module Learning
  # Records an answer (docs/ARCHITECTURE.md §5.2). Every attempt counts toward the crowd
  # tally; only a learner's first attempt on an item moves ratings and earns XP.
  class RecordAttempt
    XP_FOR_ANSWERING = 5
    XP_FOR_CORRECT = 5
    XP_FOR_BEATING_THE_ODDS = 5 # correct on an item rated well above the learner

    Result = Data.define(:attempt, :rating_changes, :xp_awarded)

    def self.call(...) = new(...).call

    def initialize(user:, item:, chosen_label:, time_ms: nil)
      @user = user
      @item = item
      @version = item.current_version or raise ArgumentError, "item has no current version"
      @chosen_label = chosen_label
      @time_ms = time_ms
    end

    def call
      record(allow_rated: true)
    rescue ActiveRecord::RecordNotUnique
      # A concurrent first attempt by the same learner won the race; record this one as a repeat.
      record(allow_rated: false)
    end

    private

    def record(allow_rated:)
      ApplicationRecord.transaction do
        @item.lock!
        correct = @chosen_label == @version.correct_label
        ChoiceTally.increment!(@version, @chosen_label)
        if allow_rated && !Attempt.exists?(user: @user, item: @item, rated: true)
          rated_attempt(correct)
        else
          unrated_attempt(correct)
        end
      end
    end

    def unrated_attempt(correct)
      attempt = Attempt.create!(base_attributes(correct).merge(rated: false))
      Result.new(attempt: attempt, rating_changes: {}, xp_awarded: 0)
    end

    def rated_attempt(correct)
      ratings = @item.skill_chain.map { |skill| @user.rating_for(skill).tap(&:lock!) }
      specific = ratings.first
      item_before = @item.rating
      user_before = specific.rating

      _, item_after = Elo.update(user_rating: user_before, item_rating: item_before, correct: correct,
                                 user_attempts: specific.attempts, item_attempts: @item.attempts_count)

      changes = ratings.to_h do |rating|
        before = rating.rating
        after, _ = Elo.update(user_rating: before, item_rating: item_before, correct: correct,
                              user_attempts: rating.attempts, item_attempts: @item.attempts_count)
        rating.update!(rating: after, attempts: rating.attempts + 1, correct: rating.correct + (correct ? 1 : 0))
        [ rating.skill, { before: before, after: after } ]
      end

      @item.update!(rating: item_after, attempts_count: @item.attempts_count + 1,
                    correct_count: @item.correct_count + (correct ? 1 : 0))

      xp = xp_for(correct, item_before, user_before)
      @user.increment!(:xp, xp)

      attempt = Attempt.create!(base_attributes(correct).merge(
        rated: true,
        user_rating_before: user_before, user_rating_after: changes.dig(specific.skill, :after),
        item_rating_before: item_before, item_rating_after: item_after
      ))
      Result.new(attempt: attempt, rating_changes: changes, xp_awarded: xp)
    end

    def xp_for(correct, item_rating, user_rating)
      xp = XP_FOR_ANSWERING
      xp += XP_FOR_CORRECT if correct
      xp += XP_FOR_BEATING_THE_ODDS if correct && item_rating >= user_rating + 100
      xp
    end

    def base_attributes(correct)
      { user: @user, item: @item, item_version: @version, chosen_label: @chosen_label,
        correct: correct, time_ms: @time_ms, skill: @item.skill }
    end
  end
end
