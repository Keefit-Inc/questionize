require "test_helper"

class Learning::RecordAttemptTest < ActiveSupport::TestCase
  setup do
    @user = User.create!
    @item = create_item(correct_label: "B")
  end

  test "first attempt is rated and moves subtype, family and overall ratings" do
    result = Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "B", time_ms: 42_000)

    assert result.attempt.rated
    assert result.attempt.correct
    assert_equal %w[CR:assumption CR overall], result.rating_changes.keys
    result.rating_changes.each_value { |change| assert_in_delta 1520.0, change[:after], 1e-9 }
    assert_in_delta 1484.0, @item.reload.rating, 1e-9
    assert_equal 1, @item.attempts_count
    assert_equal 1, @item.correct_count
    assert_equal 10, @user.reload.xp
  end

  test "only the first attempt is rated; repeats still count in the crowd tally" do
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "D")
    rating_after_first = @user.rating_for("CR:assumption").rating
    repeat = Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "B")

    assert_not repeat.attempt.rated
    assert_empty repeat.rating_changes
    assert_equal 0, repeat.xp_awarded
    assert_equal rating_after_first, @user.rating_for("CR:assumption").reload.rating
    assert_equal 1, @item.reload.attempts_count
    assert_equal({ "A" => 0, "B" => 1, "C" => 0, "D" => 1, "E" => 0 }, @item.current_version.tally)
  end

  test "a wrong first answer lowers the learner and raises the item" do
    result = Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "A")
    assert_not result.attempt.correct
    assert_operator result.rating_changes.dig("CR:assumption", :after), :<, 1500
    assert_operator @item.reload.rating, :>, 1500
    assert_equal 5, result.xp_awarded
  end

  test "beating a much harder item earns bonus XP" do
    hard = create_item(difficulty: "hard", correct_label: "C")
    result = Learning::RecordAttempt.call(user: @user, item: hard, chosen_label: "C")
    assert_equal 15, result.xp_awarded
  end

  test "the database refuses a second rated attempt for the same learner and item" do
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "B")
    duplicate = Learning::Attempt.new(user: @user, item: @item, item_version: @item.current_version,
                                      chosen_label: "B", correct: true, rated: true, skill: @item.skill)
    assert_raises(ActiveRecord::RecordNotUnique) { duplicate.save!(validate: false) }
  end

  test "different learners are rated independently" do
    other = User.create!
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "B")
    result = Learning::RecordAttempt.call(user: other, item: @item, chosen_label: "B")
    assert result.attempt.rated
    assert_equal 2, @item.reload.attempts_count
  end
end
