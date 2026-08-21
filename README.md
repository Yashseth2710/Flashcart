# FlashCart

Buy before it's gone. Built to handle the rush.

FlashCart is a flash-sale storefront for limited inventory. When a few hundred people go for
fifty units at the same moment, the hard part is not the shop — it is making sure fifty units
sell and no more. That is what this codebase is about: stock reservations held in a
transaction, availability checked under a row lock, and a checkout that will not create the
same order twice.

## How it works

A sale runs for a fixed window and allocates a set quantity to each product. Reserving does
not buy the item; it holds one for a few minutes and starts a clock. Finish checkout inside
the window and the hold becomes an order. Miss it and the stock returns to the pool for
whoever is next.

Stock is tracked as three numbers, and the difference is what anyone can still take:

    available = total - reserved - sold

PostgreSQL owns those numbers. Nothing else is allowed to be the authority on them.

## Stack

Next.js and TypeScript on the front, FastAPI and SQLAlchemy behind it, Neon PostgreSQL
underneath. Playwright and Pytest for tests, deployed on Vercel.

## Running it

Setup instructions land with the first working slice.
