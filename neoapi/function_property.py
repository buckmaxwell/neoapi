from neomodel.properties import validator
from neomodel import Property


class FunctionProperty(Property):
    @validator
    def inflate(self, value):
        return str(value)

    @validator
    def deflate(self, value):
        return str(value)

    def default_value(self):
        return str(super(FunctionProperty, self).default_value())
