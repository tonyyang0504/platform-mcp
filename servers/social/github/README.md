# GitHub MCP server

Category: **social** · Docs: https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/github.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user` (https://docs.github.com/en/rest/users/users#get-the-authenticated-user)
- `read_comments` — `POST /graphql` (https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#discussion)
- `delete` — `POST /graphql` (https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#deletediscussion)
- `analytics_post` — `POST /graphql` (https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#discussion)
- ~~`publish_text`~~ not offered: createDiscussion requires a title as well as a body, plus repositoryId and categoryId ('title: String! The title of the new discussion', https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#creatediscussion); the vocabulary input carries only text, and splitting a title out of it would be a guess.
- ~~`publish_image`~~ not offered: Discussions take Markdown bodies only; there is no image upload in the GraphQL API (https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#creatediscussion).
- ~~`reply_comment`~~ not offered: addDiscussionComment requires the discussion's node id (discussionId: ID!) besides replyToId (https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions#adddiscussioncomment); a comment id alone cannot address it.
- ~~`read_mentions`~~ not offered: The GraphQL Discussions API has no mentions feed; mentions surface as notifications (REST GET /notifications) that mix every reason and cannot be filtered to mentions server-side (https://docs.github.com/en/rest/activity/notifications).

## Credentials

- `PLATFORM_MCP_GITHUB_TOKEN` — GitHub personal access token (fine-grained: repository permission Discussions read / write on the repositories used; classic: repo or public_repo scope) sent as 'Authorization: bearer TOKEN' (https://docs.github.com/en/graphql/guides/forming-calls-with-graphql).

## Run

    uvx platform-mcp-hub serve github          # Python
    npx -y platform-mcp-hub serve github       # TypeScript
    claude mcp add github -- uvx platform-mcp-hub serve github

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/github-mcp`. Python and TypeScript serve identical tools.
