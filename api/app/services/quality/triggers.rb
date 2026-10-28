module Quality
  # Decides when an item goes back for re-review (docs/ARCHITECTURE.md §5.4):
  # - three flags with the same reason on the current version;
  # - a flag from a learner rated well above the item in that skill;
  # - crowd disagreement: at least 20 rated answers, and among learners rated above the item
  #   the most chosen option is not the key and holds more than 45%.
  class Triggers
    SAME_REASON_FLAGS = 3
    STRONG_MARGIN = 150
    STRONG_MIN_ATTEMPTS = 10
    CROWD_MIN_ATTEMPTS = 20
    CROWD_SHARE = 0.45

    def self.check(item) = new(item).check

    def initialize(item)
      @item = item
      @version = item.current_version
    end

    # Starts a review and returns its trigger, or nil when nothing calls for one.
    def check
      return unless @item.status == "verified"

      trigger = flag_trigger || crowd_trigger
      start_review(trigger) if trigger
      trigger
    end

    def crowd_stats
      strong = strong_attempts
      top, count = strong.group(:chosen_label).count.max_by { |_, n| n }
      {
        attempts: @version.choice_tallies.sum(:count),
        tally: @version.tally,
        strong_top_choice: top,
        strong_top_share: strong.any? && count ? (count.to_f / strong.count).round(3) : nil
      }
    end

    private

    def flag_trigger
      flags = @version.feedbacks.where(kind: "flag")
      return "repeated_flags" if flags.group(:reason).count.values.any? { _1 >= SAME_REASON_FLAGS }

      strong_flag = flags.joins(user: :skill_ratings).where(skill_ratings: { skill: @item.skill })
                         .where("skill_ratings.attempts >= ? AND skill_ratings.rating >= ?", STRONG_MIN_ATTEMPTS, @item.rating + STRONG_MARGIN)
      "strong_learner_flag" if strong_flag.exists?
    end

    def crowd_trigger
      rated = Learning::Attempt.where(item_version: @version, rated: true)
      return if rated.count < CROWD_MIN_ATTEMPTS

      strong = strong_attempts
      return if strong.none?

      top, count = strong.group(:chosen_label).count.max_by { |_, n| n }
      "crowd_disagreement" if top != @version.correct_label && count.to_f / strong.count > CROWD_SHARE
    end

    def strong_attempts
      Learning::Attempt.where(item_version: @version, rated: true).where("user_rating_before > item_rating_before")
    end

    def start_review(trigger)
      review = nil
      @item.with_lock do
        return unless @item.status == "verified"

        @item.update!(status: "under_review")
        review = @item.reviews.create!(from_version: @version, trigger: trigger)
      end
      ReviewItemJob.perform_later(review.id)
    end
  end
end
