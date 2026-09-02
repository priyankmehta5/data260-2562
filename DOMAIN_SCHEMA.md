# Municipal Transit Incident Domain Schema

## Personal Configuration

| Configuration | Value |
|---|---|
| SID4 | 2562 |
| PORT_BASE | 8762 |
| PREFIX | s2562 |
| SEED | 2562 |
| VERIFY_SEED | 262562 |
| DOMAIN_ID | 2 |
| Assigned Domain | Municipal transit incidents |

## Entity

The entity used in this application is a **Municipal Transit Incident**.

A municipal transit incident represents an event affecting the normal operation,
availability, safety, or infrastructure of a public transportation service.

## Entity Fields

| Field Name | Data Type | Required | Description |
|---|---|---|---|
| incidentTitle | string | Yes | Short title identifying the transit incident |
| transitRoute | string | Yes | Bus, rail, or municipal transit route affected by the incident |
| submitterEmail | email | Yes | Email address of the person submitting the incident |
| incidentDescription | string | Yes | Detailed description containing more than 25 characters |
| incidentCategory | string | Yes | Category used to classify the incident |
| termsAccepted | boolean | Yes | Indicates whether the terms and conditions were accepted |
| submissionDate | datetime | Generated | Date and time at which the form was successfully submitted |

## Category Values

The `incidentCategory` field accepts one of the following values:

1. Delay
2. Service Disruption
3. Safety Incident
4. Infrastructure Issue

## Validation Rules

1. `incidentTitle` is required.
2. `transitRoute` is required.
3. `submitterEmail` is required and must be a valid email address.
4. `incidentDescription` is required and must contain more than 25 characters.
5. `incidentCategory` must contain one of the four defined category values.
6. `termsAccepted` must be true before the form can be submitted.
7. `submissionDate` is added automatically after successful validation.