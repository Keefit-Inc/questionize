module Learning
  # What to practice next (docs/LEARNING_MODEL.md §3): bank questions at the learner's level, on
  # their weakest skills, pitched where they should get about seven in ten right.
  class Recommend
    # An item rated this far below the learner gives about a 70% chance of a right answer (Elo).
    TARGET_OFFSET = 150
    WEAKEST = 2

    Pick = Data.define(:item, :reason)

    def self.call(...) = new(...).call

    def initialize(user:, limit: 5)
      @user = user
      @limit = limit
      @level = Level.for(user)
    end

    def call
      picks = weakest_skills.flat_map { |rating| for_skill(rating) }
      picks += fill(exclude: picks.map { _1.item.id }) if picks.size < @limit
      picks.first(@limit)
    end

    private

    def pool
      @pool ||= Item.listed.where(level: @level).where.not(id: Attempt.where(user: @user).select(:item_id))
    end

    # Sub-type ratings (family:subtype) with at least one answer, lowest first.
    def weakest_skills
      @user.skill_ratings.where("skill LIKE '%:%'").where("attempts > 0").order(:rating).limit(WEAKEST).to_a
    end

    def for_skill(rating)
      family, subtype = rating.skill.split(":", 2)
      target = rating.rating - TARGET_OFFSET
      items = pool.where(family: family, subtype: subtype).order(Arel.sql(ActiveRecord::Base.sanitize_sql_array([ "ABS(items.rating - ?)", target ]))).limit(@limit)
      label = subtype.tr("_", " ")
      items.map { Pick.new(item: _1, reason: "#{label.capitalize} is one of your weaker skills (rating #{rating.rating.round})") }
    end

    # New learners, or nothing left on their weak skills: the newest questions at their level.
    def fill(exclude:)
      overall = @user.skill_ratings.find_by(skill: "overall")&.rating || 1500
      pool.where.not(id: exclude).order(Arel.sql(ActiveRecord::Base.sanitize_sql_array([ "ABS(items.rating - ?)", overall - TARGET_OFFSET ]))).limit(@limit)
          .map { Pick.new(item: _1, reason: "Matched to your level") }
    end
  end
end
