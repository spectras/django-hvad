from rest_framework import serializers
from collections import OrderedDict

class TranslatableModelOptionsMixin(object):
    def __init__(self, meta):
        super(TranslatableModelOptionsMixin, self).__init__(meta)
        # We need this ugly hack as ModelSerializer hardcodes a read_only_fields check
        self.translated_read_only_fields = getattr(meta, 'translated_read_only_fields', ())
        self.translated_write_only_fields = getattr(meta, 'translated_write_only_fields', ())

class TranslatableModelSerializerOptions(TranslatableModelOptionsMixin,
                                         serializers.ModelSerializerOptions):
    pass

class HyperlinkedTranslatableModelSerializerOptions(TranslatableModelOptionsMixin,
                                                    serializers.HyperlinkedModelSerializerOptions):
    pass

class TranslatableModelMixin(object):
    def get_default_fields(self):
        fields = super(TranslatableModelMixin, self).get_default_fields()
        fields.update(self._get_translated_fields())
        return fields

    def _get_translated_fields(self):
        ret = OrderedDict()
        trans_model = self.opts.model._meta.translations_model
        opts = trans_model._meta

        forward_rels = [field for field in opts.fields
                        if field.serialize and not field.name in ('id', 'master')]

        for trans_field in forward_rels:
            if trans_field.rel:
                raise RuntimeError()
            field = self.get_field(trans_field)
            if field:
                ret[trans_field.name] = field

        for field_name in self.opts.translated_read_only_fields:
            assert field_name in ret
            ret[field_name].read_only = True

        for field_name in self.opts.translated_write_only_fields:
            assert field_name in ret
            ret[field_name].write_only = True

        return ret

    def restore_object(self, attrs, instance=None):
        new_attrs = attrs.copy()
        lang = attrs['language_code']
        del new_attrs['language_code']

        if instance is None:
            # create an empty instance, pre-translated
            instance = self.opts.model()
            instance.translate(lang)
        else:
            # check we are updating the correct translation
            tcache = self.opts.model._meta.translations_cache
            translation = getattr(instance, tcache, None)
            if not translation or translation.language_code != lang:
                # nope, get the translation we are updating, or create it if needed
                try:
                    translation = instance.translations.get_language(lang)
                except instance.translations.model.DoesNotExist:
                    instance.translate(lang)
                else:
                    setattr(instance, tcache, translation)

        return super(TranslatableModelMixin, self).restore_object(new_attrs, instance)

class TranslatableModelSerializer(TranslatableModelMixin, serializers.ModelSerializer):
    _options_class = TranslatableModelSerializerOptions

class HyperlinkedTranslatableModelSerializer(TranslatableModelMixin,
                                             serializers.HyperlinkedModelSerializer):
    _options_class = HyperlinkedTranslatableModelSerializerOptions
