# NeoAPI - the perfect tool for building python APIs with neo4j


What you can do:
 
 * Create powerful APIs that conform to the json api specification in minutes
 * Leverage the power of the neomodel OGM and py2neo to create beautiful models with great functionality.
 

## Installation

```sh
$ pip install neoapi
```
Thats all!

## Getting Started

To get started with NeoAPI it makes sense to familiarize yourself with [NeoModel](http://neomodel.readthedocs.org/en/latest/) and [the json api specification](http://jsonapi.org/).  These are the two technologies NeoAPI is built on.  

Chances are though, you want to get started right now!! If that's the case, please check out our [sample project](https://github.com/buckmaxwell/sample-neo-api). If you get stuck, do the reading I suggested above, or drop me an email at maxbuckdeveloper@gmail.com.


# Overview of Public Methods


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