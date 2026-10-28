# Questionize API (Rails 8)

Owns all persistent state: users, the shared question bank, attempts and ratings (`Learning::`), and the knowledge model (`Knowledge::`). See `../docs/ARCHITECTURE.md` and `../docs/KNOWLEDGE_MODEL.md`.

```bash
bin/setup            # install gems, create and migrate the databases (needs PostgreSQL)
bin/rails test
bin/dev
```

Configuration lives in environment variables; see `.env.example`. Production uses `SECRET_KEY_BASE` rather than encrypted credentials.

Key code:

- `app/services/learning/elo.rb` — rating math (§5.3)
- `app/services/learning/record_attempt.rb` — attempt recording; only a learner's first attempt on an item is rated
- `app/models/knowledge/` — competencies, misconceptions, trap patterns, versioned blueprints, status lifecycle
