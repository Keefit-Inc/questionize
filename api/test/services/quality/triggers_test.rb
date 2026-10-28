require "test_helper"

class Quality::TriggersTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper

  setup { @item = create_item(correct_label: "B") }

  def flag(reason, user: User.create!)
    Learning::RecordAttempt.call(user: user, item: @item, chosen_label: "A")
    Feedback.create!(user: user, item_version: @item.current_version, kind: "flag", reason: reason)
  end

  test "three flags with the same reason start a review" do
    2.times { flag("two_answers") }
    flag("typo")
    assert_nil Quality::Triggers.check(@item.reload)

    flag("two_answers")
    assert_enqueued_with(job: ReviewItemJob) { assert_equal "repeated_flags", Quality::Triggers.check(@item.reload) }
    assert_equal "under_review", @item.reload.status
    assert_equal "repeated_flags", @item.reviews.sole.trigger
    assert_nil Quality::Triggers.check(@item), "an item under review is not queued twice"
  end

  test "one flag from a learner rated well above the item is enough" do
    strong = User.create!
    strong.skill_ratings.create!(skill: @item.skill, rating: 1800, attempts: 40, correct: 35)
    flag("wrong_key", user: strong)
    assert_equal "strong_learner_flag", Quality::Triggers.check(@item.reload)
  end

  test "stronger learners converging on a non-key option is crowd disagreement" do
    @item.update!(rating: 1300)
    20.times do |i|
      user = User.create!
      user.skill_ratings.create!(skill: @item.skill, rating: 1600)
      %w[CR overall].each { |s| user.skill_ratings.create!(skill: s, rating: 1600) }
      Learning::RecordAttempt.call(user: user, item: @item.reload, chosen_label: i < 12 ? "D" : "B")
    end
    stats = Quality::Triggers.new(@item.reload).crowd_stats
    assert_equal "D", stats[:strong_top_choice]
    assert_operator stats[:strong_top_share], :>, 0.45
    assert_equal "crowd_disagreement", Quality::Triggers.check(@item)
  end
end
