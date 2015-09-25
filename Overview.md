# Overview of Public Methods

This serves as a quick overview of the public methods specific to SerializableStructuredNode for the latest version. All
NeoModel methods are still present. To create a 'magic' api, simply make the correct models -- see the 
[sample project](https://github.com/buckmaxwell/sample-neo-api), and then create an endpoint that returns model.method()
for the correct HTTP verb.  It's that easy.


## Resource Methods
*deprecated methods not listed*

#### CRUD
* create_resource
  * POST
* update_resource
  * PATCH
* deactivate_resource
  * DELETE

#### Fetching
* get_resource
* get_collection

## Relationship methods
*deprecated methods not listed*

#### CRUD
* create_relationship -- *Many*
  * POST
* update_relationship -- *One or Many*
  * PATCH
* disconnect_relationship -- *Many*
  * DELETE

#### Fetching
* get_relationship