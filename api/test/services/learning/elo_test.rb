require "test_helper"

class Learning::EloTest < ActiveSupport::TestCase
  test "expected score is one half for equal ratings and rises with the rating gap" do
    assert_in_delta 0.5, Learning::Elo.expected(1500, 1500), 1e-9
    assert_in_delta 0.909, Learning::Elo.expected(1900, 1500), 0.001
    assert_in_delta 0.091, Learning::Elo.expected(1500, 1900), 0.001
  end

  test "step sizes shrink with experience" do
    assert_equal [ 40.0, 40.0, 24.0, 24.0, 16.0 ], [ 0, 19, 20, 99, 100 ].map { Learning::Elo.k_user(_1) }
    assert_equal [ 32.0, 32.0, 12.0 ], [ 0, 29, 30 ].map { Learning::Elo.k_item(_1) }
  end

  test "a correct answer on an even item moves both ratings by half the step" do
    user, item = Learning::Elo.update(user_rating: 1500, item_rating: 1500, correct: true, user_attempts: 0, item_attempts: 0)
    assert_in_delta 1520.0, user, 1e-9
    assert_in_delta 1484.0, item, 1e-9
  end

  test "missing an easy item costs more than missing a hard one" do
    easy_miss, = Learning::Elo.update(user_rating: 1500, item_rating: 1300, correct: false, user_attempts: 0, item_attempts: 0)
    hard_miss, = Learning::Elo.update(user_rating: 1500, item_rating: 1700, correct: false, user_attempts: 0, item_attempts: 0)
    assert_operator 1500 - easy_miss, :>, 1500 - hard_miss
  end
end
