# selectry taxonomy MVP implementation runbook

This runbook implements the portal-first Azure AI Search ESCO/O*NET skill
matching MVP.

## 1. Azure Storage

Create a Storage Account:

- Resource group: `rg-powerplatform-billing`
- Name: `selectrytaxonomydata`
- Region: `Germany West Central`
- Performance: `Standard`
- Redundancy: `LRS`

Create a private Blob container:

- Container name: `taxonomy-source`

## 2. Azure AI Search index

In `azureaisearchselectry`, create index `selectry-skills-v2`.

Use the JSON schema in:

```text
taxonomy_mvp/selectry-skills-v2.index.json
```

## 3. selectry-local seed data

Upload modern tool data directly to the new index.

Request:

```text
POST https://azureaisearchselectry.search.windows.net/indexes/selectry-skills-v2/docs/index?api-version=2024-07-01
```

Headers:

```text
Content-Type: application/json
api-key: <admin-key>
```

Body:

```text
taxonomy_mvp/selectry-local-skills.json
```

## 4. ESCO transform

Download English ESCO skills/competences CSV from:

```text
https://esco.ec.europa.eu/en/use-esco/download
```

Transform it:

```bash
python3 taxonomy_mvp/prepare_taxonomy.py \
  --source ESCO \
  --input /path/to/esco_skills_en.csv \
  --output taxonomy_mvp/out/esco-skills-upload.json
```

Upload `taxonomy_mvp/out/esco-skills-upload.json` to the same Azure Search index
using the same `/docs/index` endpoint as above.

## 5. O*NET transform

Download O*NET database files from:

```text
https://www.onetcenter.org/
```

Start with skills, knowledge, abilities, and technology skills files.

Transform each file:

```bash
python3 taxonomy_mvp/prepare_taxonomy.py \
  --source ONET \
  --input /path/to/onet_file.csv \
  --output taxonomy_mvp/out/onet-upload.json
```

Upload each transformed JSON file to `selectry-skills-v2`.

## 6. Search Explorer tests

Use `selectry-skills-v2`.

Test software development:

```json
{
  "search": "software development",
  "queryType": "simple",
  "top": 5,
  "select": "id,source,preferredLabel,altLabels,description,skillType,uri"
}
```

Test Docker:

```json
{
  "search": "Docker",
  "queryType": "simple",
  "top": 5,
  "select": "id,source,preferredLabel,altLabels,description,skillType,uri"
}
```

Test project management:

```json
{
  "search": "project management",
  "queryType": "simple",
  "top": 5,
  "select": "id,source,preferredLabel,altLabels,description,skillType,uri"
}
```

## 7. Power Automate update

In `PA_GetSkillTaxonomyMatches_v2`, update the HTTP URI:

```text
https://azureaisearchselectry.search.windows.net/indexes/selectry-skills-v2/docs/search?api-version=2024-07-01
```

Keep the body expression:

```text
json(concat('{"search":"', item(), '","queryType":"simple","top":3,"select":"id,source,preferredLabel,altLabels,description,skillType,uri"}'))
```

The last action must be `Return value(s) to Power Virtual Agents`, not generic
`Response`.

Return:

```text
taxonomyStatus = taxonomy_lookup_completed
taxonomyMatchesJson = string(variables('varResults'))
taxonomySourcesUsedJson = ["ESCO","O*NET","selectry-local"]
```

## 8. Copilot Studio tool and agent

Tool display name:

```text
Match job skills against ESCO and O*NET skill databases
```

Underlying flow:

```text
PA_GetSkillTaxonomyMatches_v2
```

Model:

```text
Claude Sonnet 4.6
```

Behavior:

- Input is role core JSON from Agent 1.
- Extract unique skill names.
- Call the taxonomy flow with a JSON string array.
- Preserve original priority and source.
- Use taxonomy only as enrichment.
- Do not invent ESCO/O*NET matches.
- Do not promote optional/unconfirmed signals to must-have.
