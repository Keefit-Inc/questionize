# Sends an item under review to the AI service and applies the verdict (docs/ARCHITECTURE.md §5.4).
# "revise" with a verified revision creates a new version; tallies and the item's rating carry
# over only when the key is unchanged. Attempts stay linked to the version they answered.
class ReviewItemJob < ApplicationJob
  queue_as :default

  class_attribute :ai_client_factory, default: -> { AiService::Client.new }

  def perform(review_id)
    review = ItemReview.find(review_id)
    item = review.item
    version = review.from_version
    flags = version.feedbacks.where(kind: "flag").map { |f| { reason: f.reason, comment: f.comment.to_s } }
    result = ai_client_factory.call.review(question: version.to_question, flags: flags, crowd: Quality::Triggers.new(item).crowd_stats)
    decision = result.fetch("decision")
    review.update!(verdict: decision["verdict"], findings: decision["findings"])

    case decision["verdict"]
    when "keep" then finish(review, item, "verified")
    when "retire" then finish(review, item, "retired")
    when "revise" then revise(review, item, version, result["revised"])
    end
  rescue AiService::Error => e
    Rails.logger.error("[ReviewItemJob] review #{review_id}: #{e.message}")
    review&.update!(status: "failed")
    review&.item&.update!(status: "flagged") # needs a person
  end

  private

  def finish(review, item, status)
    item.update!(status: status)
    review.update!(status: "done")
  end

  def revise(review, item, old, revised)
    unless revised && revised.dig("verification", "verified")
      item.update!(status: "flagged") # the revision did not verify; a person should look
      return review.update!(status: "done")
    end

    Item.transaction do
      version = ItemVersion.create_from_generated!(item: item, generated: revised, version: item.versions.maximum(:version) + 1, parent: old)
      if version.correct_label == old.correct_label
        rows = old.choice_tallies.map { |t| { item_version_id: version.id, label: t.label, count: t.count } }
        Learning::ChoiceTally.insert_all!(rows) if rows.any?
        item.update!(current_version: version, status: "verified")
      else
        item.update!(current_version: version, status: "verified", rating: Item.start_rating("medium"), attempts_count: 0, correct_count: 0)
      end
      review.update!(to_version: version, status: "done")
    end
  end
end
