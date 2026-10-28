module Learning
  # Elo-style rating math (docs/ARCHITECTURE.md §5.3). Pure functions, no persistence.
  module Elo
    module_function

    START_RATING = 1500.0

    def expected(user_rating, item_rating)
      1.0 / (1.0 + 10.0**((item_rating - user_rating) / 400.0))
    end

    # Step size shrinks as a learner accumulates rated attempts in a skill.
    def k_user(rated_attempts)
      if rated_attempts < 20 then 40.0
      elsif rated_attempts < 100 then 24.0
      else 16.0
      end
    end

    def k_item(rated_attempts)
      rated_attempts < 30 ? 32.0 : 12.0
    end

    # Returns [new_user_rating, new_item_rating].
    def update(user_rating:, item_rating:, correct:, user_attempts:, item_attempts:)
      score = correct ? 1.0 : 0.0
      surprise = score - expected(user_rating, item_rating)
      [ user_rating + k_user(user_attempts) * surprise, item_rating - k_item(item_attempts) * surprise ]
    end
  end
end
