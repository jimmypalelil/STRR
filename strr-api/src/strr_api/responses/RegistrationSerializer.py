"""
Registration response objects.
"""
from typing import Optional

from strr_api.enums.enum import RegistrationStatus, RegistrationType
from strr_api.models import (
    Application,
    Platform,
    PlatformRegistration,
    PropertyContact,
    PropertyManager,
    Registration,
    RentalProperty,
    StrataHotel,
    StrataHotelRegistration,
)


class RegistrationSerializer:
    """Registration response serializer."""

    HOST_STATUSES = {
        RegistrationStatus.ACTIVE: "Registered",
        RegistrationStatus.EXPIRED: "Expired",
        RegistrationStatus.SUSPENDED: "Suspended",
        RegistrationStatus.CANCELLED: "Cancelled",
    }

    HOST_ACTIONS = {
        RegistrationStatus.EXPIRED: ["REAPPLY"],
    }

    EXAMINER_STATUSES = {
        RegistrationStatus.ACTIVE: "Registered",
        RegistrationStatus.EXPIRED: "Expired",
        RegistrationStatus.SUSPENDED: "Suspended",
        RegistrationStatus.CANCELLED: "Cancelled",
    }

    EXAMINER_ACTIONS = {
        RegistrationStatus.ACTIVE: ["APPROVE", "SUSPEND", "CANCEL", "SET_ASIDE"],
        RegistrationStatus.SUSPENDED: ["REINSTATE", "CANCEL", "SET_ASIDE"],
        RegistrationStatus.CANCELLED: ["SET_ASIDE"],
        RegistrationStatus.EXPIRED: [],
    }

    @classmethod
    def serialize(cls, registration: Registration, applications: list | None = None):
        """Return a Registration object from a database model.

        When ``applications`` is provided (e.g. batch-loaded for a search page), it is used
        for header applications and host jurisdiction/strRequirements instead of querying
        per registration.
        """
        registration_data = {
            "id": registration.id,
            "user_id": registration.user_id,
            "sbc_account_id": registration.sbc_account_id,
            "registrationType": registration.registration_type,
            "updatedDate": registration.updated_date.isoformat(),
            "cancelledDate": registration.cancelled_date.isoformat() if registration.cancelled_date else None,
            "startDate": registration.start_date.isoformat() if registration.start_date else None,
            "expiryDate": registration.expiry_date.isoformat() if registration.expiry_date else None,
            "status": registration.status.name,
            "registrationNumber": registration.registration_number,
            "nocStatus": registration.noc_status.name if registration.noc_status else None,
            "provisionalExtensionApplied": registration.provisional_extension_applied,
        }

        if registration.noc_status and registration.nocs:
            latest_noc = max(registration.nocs, key=lambda noc: noc.start_date)
            registration_data["nocStartDate"] = latest_noc.start_date.isoformat()
            registration_data["nocEndDate"] = latest_noc.end_date.isoformat()

        if registration.conditionsOfApproval:
            registration_data["conditionsOfApproval"] = {
                "predefinedConditions": registration.conditionsOfApproval.preapproved_conditions,
                "customConditions": registration.conditionsOfApproval.custom_conditions,
                "minBookingDays": registration.conditionsOfApproval.minBookingDays,
            }

        # Include snapshot details
        if registration.snapshots:
            registration_data["snapshots"] = [
                {
                    "id": snapshot.id,
                    "version": snapshot.version,
                    "snapshotDateTime": snapshot.snapshot_datetime.isoformat() if snapshot.snapshot_datetime else None,
                    "snapshotEndpoint": f"/registrations/{registration.id}/snapshots/{snapshot.id}",
                }
                for snapshot in sorted(registration.snapshots, key=lambda s: s.version, reverse=True)
            ]

        RegistrationSerializer._populate_header_data(registration_data, registration, applications=applications)

        documents = []
        if registration.documents:
            for doc in registration.documents:
                # Use added_on when set, otherwise document upload time from documents.created
                added_on_value = doc.added_on if doc.added_on is not None else getattr(doc, "created", None)
                documents.append(
                    {
                        "fileKey": doc.path,
                        "fileName": doc.file_name,
                        "fileType": doc.file_type,
                        "documentType": doc.document_type,
                        "addedOn": added_on_value.isoformat() if added_on_value else None,
                    }
                )
        registration_data["documents"] = documents

        if registration.registration_type == RegistrationType.HOST.value:
            RegistrationSerializer.populate_host_registration_details(
                registration_data, registration, applications=applications
            )

        elif registration.registration_type == RegistrationType.PLATFORM.value:
            RegistrationSerializer.populate_platform_registration_details(registration_data, registration)

        elif registration.registration_type == RegistrationType.STRATA_HOTEL.value:
            RegistrationSerializer.populate_strata_hotel_registration_details(registration_data, registration)

        return registration_data

    @classmethod
    def serialize_for_examiner_search_list(cls, registration: Registration, applications: list | None = None):
        """Minimal registration JSON for examiner ``/registrations/search`` list rows.

        Matches fields used by the examiner dashboard table (addresses, requirements,
        adjudicator, renewal badge, recent-document indicator) without snapshots,
        conditions of approval, or large nested trees.
        """
        registration_data = {
            "id": registration.id,
            "user_id": registration.user_id,
            "sbc_account_id": registration.sbc_account_id,
            "registrationType": registration.registration_type,
            "updatedDate": registration.updated_date.isoformat(),
            "cancelledDate": registration.cancelled_date.isoformat() if registration.cancelled_date else None,
            "startDate": registration.start_date.isoformat() if registration.start_date else None,
            "expiryDate": registration.expiry_date.isoformat() if registration.expiry_date else None,
            "status": registration.status.name,
            "registrationNumber": registration.registration_number,
            "nocStatus": registration.noc_status.name if registration.noc_status else None,
            "provisionalExtensionApplied": registration.provisional_extension_applied,
            "header": {
                "isSetAside": registration.is_set_aside,
                "assignee": cls._get_user_info(registration.reviewer_id, registration.reviewer),
                "decider": cls._get_user_info(registration.decider_id, registration.decider),
                "applications": cls._application_headers_for_list(registration, applications=applications),
            },
            "documents": cls._thin_documents_for_search_list(registration),
        }

        if registration.registration_type == RegistrationType.HOST.value:
            cls._examiner_search_list_host(registration_data, registration, applications=applications)
        elif registration.registration_type == RegistrationType.PLATFORM.value:
            cls._examiner_search_list_platform(registration_data, registration)
        elif registration.registration_type == RegistrationType.STRATA_HOTEL.value:
            cls._examiner_search_list_strata(registration_data, registration)

        return registration_data

    @staticmethod
    def _thin_documents_for_search_list(registration: Registration) -> list[dict]:
        if not registration.documents:
            return []
        thin = []
        for doc in registration.documents:
            added_on_value = doc.added_on if doc.added_on is not None else getattr(doc, "created", None)
            thin.append({"addedOn": added_on_value.isoformat() if added_on_value else None})
        return thin

    @classmethod
    def _application_headers_for_list(
        cls, registration: Registration, applications: list | None = None
    ) -> list[dict]:
        if applications is None:
            applications = Application.get_all_by_registration_id(registration.id)
        if not applications:
            return []
        sorted_applications = sorted(applications, key=lambda app: app.application_date, reverse=True)
        return [
            {
                "applicationNumber": application.application_number,
                "applicationDateTime": application.application_date.isoformat(),
                "applicationType": application.type,
                "applicationStatus": application.status,
            }
            for application in sorted_applications
        ]

    @classmethod
    def _mailing_address_dict(cls, address) -> dict:
        if not address:
            return {
                "address": None,
                "addressLineTwo": None,
                "city": None,
                "postalCode": None,
                "province": None,
                "country": None,
                "locationDescription": None,
            }
        return {
            "address": address.street_address,
            "addressLineTwo": address.street_address_additional,
            "city": address.city,
            "postalCode": address.postal_code,
            "province": address.province,
            "country": address.country,
            "locationDescription": address.location_description,
        }

    @classmethod
    def _examiner_search_list_host(
        cls, registration_data: dict, registration: Registration, applications: list | None = None
    ):
        rp: RentalProperty | None = registration.rental_property
        if not rp:
            registration_data["primaryContact"] = {"firstName": None, "middleName": None, "lastName": None}
            registration_data["unitAddress"] = None
            registration_data["unitDetails"] = {
                "jurisdiction": None,
                "prRequired": None,
                "blRequired": None,
                "prExemptReason": None,
                "strataHotelCategory": None,
            }
            str_requirements = cls.get_str_requirements_from_application(registration, applications=applications)
            if str_requirements:
                registration_data["strRequirements"] = str_requirements
            return

        primary_contacts = [c for c in rp.contacts if c.is_primary]
        if not primary_contacts:
            registration_data["primaryContact"] = {"firstName": None, "middleName": None, "lastName": None}
        else:
            pc = primary_contacts[0].contact
            registration_data["primaryContact"] = {
                "firstName": pc.firstname,
                "middleName": pc.middlename,
                "lastName": pc.lastname,
            }

        registration_data["unitAddress"] = {
            "unitNumber": rp.address.unit_number,
            "streetNumber": rp.address.street_number,
            "streetName": rp.address.street_address,
            "addressLineTwo": rp.address.street_address_additional,
            "city": rp.address.city,
            "postalCode": rp.address.postal_code,
            "province": rp.address.province,
            "country": rp.address.country,
            "nickname": rp.nickname,
            "locationDescription": rp.address.location_description,
        }

        registration_data["unitDetails"] = {
            "jurisdiction": cls.get_jurisdiction_from_application(registration, applications=applications),
            "prRequired": rp.pr_required,
            "blRequired": rp.bl_required,
            "prExemptReason": rp.pr_exempt_reason,
            "strataHotelCategory": rp.strata_hotel_category.name if rp.strata_hotel_category else None,
        }

        str_requirements = cls.get_str_requirements_from_application(registration, applications=applications)
        if str_requirements:
            registration_data["strRequirements"] = str_requirements

    @classmethod
    def _examiner_search_list_platform(cls, registration_data: dict, registration: Registration):
        pr: PlatformRegistration | None = registration.platform_registration
        if not pr or not pr.platform:
            registration_data["businessDetails"] = {
                "legalName": None,
                "mailingAddress": cls._mailing_address_dict(None),
            }
            registration_data["platformDetails"] = {"listingSize": None, "documents": []}
            return

        platform: Platform = pr.platform
        registration_data["businessDetails"] = {
            "legalName": platform.legal_name,
            "mailingAddress": cls._mailing_address_dict(platform.mailingAddress),
        }
        thin_docs = cls._thin_documents_for_search_list(registration)
        registration_data["platformDetails"] = {
            "listingSize": platform.listing_size,
            "documents": thin_docs,
        }

    @classmethod
    def _examiner_search_list_strata(cls, registration_data: dict, registration: Registration):
        shr: StrataHotelRegistration | None = registration.strata_hotel_registration
        if not shr or not shr.strata_hotel:
            registration_data["businessDetails"] = {"legalName": None}
            registration_data["strataHotelDetails"] = {
                "location": cls._mailing_address_dict(None),
                "documents": [],
            }
            return

        strata_hotel: StrataHotel = shr.strata_hotel
        registration_data["businessDetails"] = {"legalName": strata_hotel.legal_name}
        loc = strata_hotel.location
        registration_data["strataHotelDetails"] = {
            "location": {
                "address": loc.street_address,
                "addressLineTwo": loc.street_address_additional,
                "city": loc.city,
                "postalCode": loc.postal_code,
                "province": loc.province,
                "country": loc.country,
                "locationDescription": loc.location_description,
            },
            "documents": [],
        }

    @classmethod
    def _populate_header_data(
        cls,
        registration_data: dict,
        registration: Registration,
        applications: list | None = None,
    ):
        """Populates header data into response object."""
        registration_data["header"] = {}
        registration_data["header"]["isSetAside"] = registration.is_set_aside
        registration_data["header"]["hostStatus"] = RegistrationSerializer.HOST_STATUSES.get(
            registration.status, registration.status.name
        )
        registration_data["header"]["hostActions"] = RegistrationSerializer.HOST_ACTIONS.get(registration.status, [])
        registration_data["header"]["examinerStatus"] = RegistrationSerializer.EXAMINER_STATUSES.get(
            registration.status, registration.status.name
        )
        registration_data["header"]["examinerActions"] = cls._get_examiner_actions(registration)
        registration_data["header"]["assignee"] = cls._get_user_info(registration.reviewer_id, registration.reviewer)
        registration_data["header"]["decider"] = cls._get_user_info(registration.decider_id, registration.decider)
        cls._populate_applications(registration_data, registration, applications=applications)

    @classmethod
    def _get_examiner_actions(cls, registration: Registration) -> list:
        """Get examiner actions based on registration state."""
        if registration.is_set_aside:
            return ["APPROVE", "CANCEL"]

        base_actions = RegistrationSerializer.EXAMINER_ACTIONS.get(registration.status, [])
        if registration.status == RegistrationStatus.ACTIVE and not registration.noc_status:
            base_actions = base_actions + ["SEND_NOC"]

        if registration.noc_status:
            return ["APPROVE", "CANCEL", "SUSPEND"]

        return base_actions

    @classmethod
    def _get_user_info(cls, user_id: int, user) -> dict:
        """Get user information for display."""
        user_info = {}
        if user_id and user:
            user_info["username"] = user.username
            display_name_parts = []
            if user.firstname:
                display_name_parts.append(user.firstname)
            if user.lastname:
                display_name_parts.append(user.lastname)
            user_info["displayName"] = " ".join(display_name_parts)
        return user_info

    @classmethod
    def _populate_applications(
        cls,
        registration_data: dict,
        registration: Registration,
        applications: list | None = None,
    ):
        """Populate applications data."""
        if applications is None:
            applications = Application.get_all_by_registration_id(registration.id)
        if not applications:
            return

        sorted_applications = sorted(applications, key=lambda app: app.application_date, reverse=True)
        registration_data["header"]["applications"] = []

        for application in sorted_applications:
            application_data = {
                "applicationNumber": application.application_number,
                "applicationDateTime": application.application_date.isoformat(),
                "applicationType": application.type,
                "applicationStatus": application.status,
                "organizationName": application.application_json.get("registration")
                .get("strRequirements", {})
                .get("organizationNm"),
            }
            application_data["assignee"] = cls._get_user_info(application.reviewer_id, application.reviewer)
            application_data["decider"] = cls._get_user_info(application.decider_id, application.decider)
            registration_data["header"]["applications"].append(application_data)

    @classmethod
    def populate_strata_hotel_registration_details(cls, registration_data: dict, registration: Registration):
        """Populates strata hotel registration details into response object."""
        strata_hotel: StrataHotel = registration.strata_hotel_registration.strata_hotel
        registration_data["businessDetails"] = {
            "legalName": strata_hotel.legal_name,
            "homeJurisdiction": strata_hotel.home_jurisdiction,
            "businessNumber": strata_hotel.business_number,
            "mailingAddress": {
                "address": strata_hotel.mailingAddress.street_address,
                "addressLineTwo": strata_hotel.mailingAddress.street_address_additional,  # noqa: E501
                "city": strata_hotel.mailingAddress.city,
                "postalCode": strata_hotel.mailingAddress.postal_code,
                "province": strata_hotel.mailingAddress.province,
                "country": strata_hotel.mailingAddress.country,
                "locationDescription": strata_hotel.mailingAddress.location_description,
            },
        }
        if strata_hotel.registered_office_attorney_mailing_address_id:
            attorney_mailing_address = strata_hotel.registered_office_attorney_mailing_address
            registration_data["businessDetails"]["registeredOfficeOrAttorneyForServiceDetails"] = {
                "attorneyName": strata_hotel.attorney_name,
                "mailingAddress": {
                    "address": attorney_mailing_address.street_address,
                    "addressLineTwo": attorney_mailing_address.street_address_additional,  # noqa: E501
                    "city": attorney_mailing_address.city,
                    "postalCode": attorney_mailing_address.postal_code,
                    "province": attorney_mailing_address.province,
                    "country": attorney_mailing_address.country,
                    "locationDescription": attorney_mailing_address.location_description,
                },
            }

        registration_data["strataHotelRepresentatives"] = [
            {
                "firstName": representative.contact.firstname,
                "middleName": representative.contact.middlename,
                "lastName": representative.contact.lastname,
                "phoneNumber": representative.contact.phone_number,
                "extension": representative.contact.phone_extension,
                "faxNumber": representative.contact.fax_number,
                "emailAddress": representative.contact.email,
                "jobTitle": representative.contact.job_title,
                "phoneCountryCode": representative.contact.phone_country_code,
            }
            for representative in strata_hotel.representatives
        ]

        buildings = [
            {
                "address": building.address.street_address,
                "addressLineTwo": building.address.street_address_additional,  # noqa: E501
                "city": building.address.city,
                "postalCode": building.address.postal_code,
                "province": building.address.province,
                "country": building.address.country,
                "locationDescription": building.address.location_description,
            }
            for building in strata_hotel.buildings
        ]
        registration_data["strataHotelDetails"] = {
            "brand": {"name": strata_hotel.brand_name, "website": strata_hotel.website},
            "location": {
                "address": strata_hotel.location.street_address,
                "addressLineTwo": strata_hotel.location.street_address_additional,  # noqa: E501
                "city": strata_hotel.location.city,
                "postalCode": strata_hotel.location.postal_code,
                "province": strata_hotel.location.province,
                "country": strata_hotel.location.country,
                "locationDescription": strata_hotel.location.location_description,
            },
            "numberOfUnits": strata_hotel.number_of_units,
            "category": strata_hotel.category,
            "buildings": buildings,
            "unitListings": strata_hotel.unit_listings,
        }

    @classmethod
    def populate_platform_registration_details(cls, registration_data: dict, registration: Registration):
        """Populates host registration details into response object."""
        platform: Platform = registration.platform_registration.platform
        registration_data["businessDetails"] = {
            "legalName": platform.legal_name,
            "homeJurisdiction": platform.home_jurisdiction,
            "businessNumber": platform.business_number,
            "consumerProtectionBCLicenceNumber": platform.cpbc_licence_number,
            "noticeOfNonComplianceEmail": platform.primary_non_compliance_notice_email,
            "noticeOfNonComplianceOptionalEmail": platform.secondary_non_compliance_notice_email,
            "takeDownRequestEmail": platform.primary_take_down_request_email,
            "takeDownRequestOptionalEmail": platform.secondary_take_down_request_email,
            "mailingAddress": {
                "address": platform.mailingAddress.street_address,
                "addressLineTwo": platform.mailingAddress.street_address_additional,  # noqa: E501
                "city": platform.mailingAddress.city,
                "postalCode": platform.mailingAddress.postal_code,
                "province": platform.mailingAddress.province,
                "country": platform.mailingAddress.country,
                "locationDescription": platform.mailingAddress.location_description,
            },
        }
        if platform.registered_office_attorney_mailing_address_id:
            attorney_mailing_address = platform.registered_office_attorney_mailing_address
            registration_data["businessDetails"]["registeredOfficeOrAttorneyForServiceDetails"] = {
                "attorneyName": platform.attorney_name,
                "mailingAddress": {
                    "address": attorney_mailing_address.street_address,
                    "addressLineTwo": attorney_mailing_address.street_address_additional,  # noqa: E501
                    "city": attorney_mailing_address.city,
                    "postalCode": attorney_mailing_address.postal_code,
                    "province": attorney_mailing_address.province,
                    "country": attorney_mailing_address.country,
                    "locationDescription": attorney_mailing_address.location_description,
                },
            }

        registration_data["platformRepresentatives"] = [
            {
                "firstName": representative.contact.firstname,
                "middleName": representative.contact.middlename,
                "lastName": representative.contact.lastname,
                "phoneNumber": representative.contact.phone_number,
                "extension": representative.contact.phone_extension,
                "faxNumber": representative.contact.fax_number,
                "emailAddress": representative.contact.email,
                "jobTitle": representative.contact.job_title,
                "phoneCountryCode": representative.contact.phone_country_code,
            }
            for representative in platform.representatives
        ]

        platform_brands = [{"name": brand.name, "website": brand.website} for brand in platform.brands]
        registration_data["platformDetails"] = {"brands": platform_brands, "listingSize": platform.listing_size}

    @classmethod
    def populate_host_registration_details(
        cls,
        registration_data: dict,
        registration: Registration,
        applications: list | None = None,
    ):
        """Populates host registration details into response object."""

        primary_property_contact = list(filter(lambda x: x.is_primary is True, registration.rental_property.contacts))[
            0
        ]
        secondary_property_contacts = list(
            filter(lambda x: x.is_primary is False, registration.rental_property.contacts)
        )
        secondary_property_contact = secondary_property_contacts[0] if secondary_property_contacts else None

        registration_data["primaryContact"] = {
            "firstName": primary_property_contact.contact.firstname,
            "middleName": primary_property_contact.contact.middlename,
            "lastName": primary_property_contact.contact.lastname,
            "dateOfBirth": primary_property_contact.contact.date_of_birth.strftime("%Y-%m-%d")
            if primary_property_contact.contact.date_of_birth
            else None,
            "socialInsuranceNumber": primary_property_contact.contact.social_insurance_number,
            "businessNumber": primary_property_contact.contact.business_number,
            "contactType": primary_property_contact.contact_type,
            "businessLegalName": primary_property_contact.business_legal_name,
            "preferredName": primary_property_contact.contact.preferredname,
            "phoneNumber": primary_property_contact.contact.phone_number,
            "phoneCountryCode": primary_property_contact.contact.phone_country_code,
            "extension": primary_property_contact.contact.phone_extension,
            "faxNumber": primary_property_contact.contact.fax_number,
            "emailAddress": primary_property_contact.contact.email,
            "mailingAddress": {
                "address": primary_property_contact.contact.address.street_address,
                "addressLineTwo": primary_property_contact.contact.address.street_address_additional,  # noqa: E501
                "city": primary_property_contact.contact.address.city,
                "postalCode": primary_property_contact.contact.address.postal_code,
                "province": primary_property_contact.contact.address.province,
                "country": primary_property_contact.contact.address.country,
            },
        }

        registration_data["secondaryContact"] = None
        if secondary_property_contact:
            registration_data["secondaryContact"] = {
                "firstName": secondary_property_contact.contact.firstname,
                "middleName": secondary_property_contact.contact.middlename,
                "lastName": secondary_property_contact.contact.lastname,
                "dateOfBirth": secondary_property_contact.contact.date_of_birth.strftime("%Y-%m-%d")
                if secondary_property_contact.contact.date_of_birth
                else None,
                "socialInsuranceNumber": secondary_property_contact.contact.social_insurance_number,
                "contactType": secondary_property_contact.contact_type,
                "businessNumber": secondary_property_contact.contact.business_number,
                "preferredName": secondary_property_contact.contact.preferredname,
                "phoneNumber": secondary_property_contact.contact.phone_number,
                "phoneCountryCode": secondary_property_contact.contact.phone_country_code,
                "extension": secondary_property_contact.contact.phone_extension,
                "faxNumber": secondary_property_contact.contact.fax_number,
                "emailAddress": secondary_property_contact.contact.email,
                "mailingAddress": {
                    "address": secondary_property_contact.contact.address.street_address,
                    "addressLineTwo": secondary_property_contact.contact.address.street_address_additional,
                    # noqa: E501
                    "city": secondary_property_contact.contact.address.city,
                    "postalCode": secondary_property_contact.contact.address.postal_code,
                    "province": secondary_property_contact.contact.address.province,
                    "country": secondary_property_contact.contact.address.country,
                },
            }

        registration_data["unitAddress"] = {
            "unitNumber": registration.rental_property.address.unit_number,
            "streetNumber": registration.rental_property.address.street_number,
            "streetName": registration.rental_property.address.street_address,
            "addressLineTwo": registration.rental_property.address.street_address_additional,
            "city": registration.rental_property.address.city,
            "postalCode": registration.rental_property.address.postal_code,
            "province": registration.rental_property.address.province,
            "country": registration.rental_property.address.country,
            "nickname": registration.rental_property.nickname,
            "locationDescription": registration.rental_property.address.location_description,
        }

        registration_data["unitDetails"] = {
            "parcelIdentifier": registration.rental_property.parcel_identifier,
            "businessLicense": registration.rental_property.local_business_licence,
            "businessLicenseExpiryDate": registration.rental_property.local_business_licence_expiry_date.strftime(
                "%Y-%m-%d"
            )
            if registration.rental_property.local_business_licence_expiry_date
            else None,
            "blExemptReason": registration.rental_property.bl_exempt_reason,
            "propertyType": registration.rental_property.property_type.name,
            "ownershipType": registration.rental_property.ownership_type,
            "rentalUnitSpaceType": registration.rental_property.space_type,
            "hostResidence": registration.rental_property.host_residence,
            "isUnitOnPrincipalResidenceProperty": registration.rental_property.is_unit_on_principal_residence_property,
            "numberOfRoomsForRent": registration.rental_property.number_of_rooms_for_rent,
            "strataHotelRegistrationNumber": registration.rental_property.strata_hotel_registration_number,
            "prExemptReason": registration.rental_property.pr_exempt_reason,
            "strataHotelCategory": registration.rental_property.strata_hotel_category,
            "jurisdiction": RegistrationSerializer.get_jurisdiction_from_application(
                registration, applications=applications
            ),
            "prRequired": registration.rental_property.pr_required,
            "blRequired": registration.rental_property.bl_required,
            "rentalUnitSetupOption": registration.rental_property.rental_space_option,
            "hostType": registration.rental_property.host_type,
        }

        # Add strRequirements from application (source of truth)
        str_requirements = RegistrationSerializer.get_str_requirements_from_application(
            registration, applications=applications
        )
        if str_requirements:
            registration_data["strRequirements"] = str_requirements

        registration_data["listingDetails"] = [
            {"url": platform.url} for platform in registration.rental_property.property_listings
        ]

        if property_manager := registration.rental_property.property_manager:
            primary_contact = property_manager.primary_contact
            contact_dict = cls._build_primary_contact_dict(primary_contact)

            if property_manager.property_manager_type == PropertyManager.PropertyManagerType.BUSINESS:
                registration_data["propertyManager"] = {
                    "business": {
                        "legalName": property_manager.business_legal_name,
                        "businessNumber": property_manager.business_number,
                        "mailingAddress": {
                            "address": property_manager.business_mailing_address.street_address,
                            "city": property_manager.business_mailing_address.city,
                            "postalCode": property_manager.business_mailing_address.postal_code,
                            "province": property_manager.business_mailing_address.province,
                            "country": property_manager.business_mailing_address.country,
                        },
                        "primaryContact": contact_dict,
                    }
                }
            else:
                registration_data["propertyManager"] = {"contact": contact_dict}
                if primary_contact and (contact_mailing_address := primary_contact.address):
                    registration_data["propertyManager"]["contact"]["mailingAddress"] = {
                        "address": contact_mailing_address.street_address,
                        "city": contact_mailing_address.city,
                        "postalCode": contact_mailing_address.postal_code,
                        "province": contact_mailing_address.province,
                        "country": contact_mailing_address.country,
                    }

            registration_data["propertyManager"]["propertyManagerType"] = property_manager.property_manager_type
            # Preserve initiatedByPropertyManager flag in registrations
            registration_data["propertyManager"]["initiatedByPropertyManager"] = cls._get_initiated_by_property_manager(
                registration
            )

    @classmethod
    def _get_initiated_by_property_manager(cls, registration: Registration) -> bool | None:
        """Get initiatedByPropertyManager from registration_json (populated at create/renewal and by backfiller)."""
        reg_json = registration.registration_json or {}
        pm = reg_json.get("propertyManager") or {}
        if isinstance(pm, dict) and "initiatedByPropertyManager" in pm:
            return bool(pm["initiatedByPropertyManager"])
        return None

    @classmethod
    def _build_primary_contact_dict(cls, primary_contact) -> dict:
        """Build a dictionary of primary contact information, handling None safely."""
        if not primary_contact:
            return {
                "firstName": None,
                "lastName": None,
                "middleName": None,
                "preferredName": None,
                "phoneNumber": None,
                "phoneCountryCode": None,
                "extension": None,
                "faxNumber": None,
                "emailAddress": None,
            }
        return {
            "firstName": primary_contact.firstname,
            "lastName": primary_contact.lastname,
            "middleName": primary_contact.middlename,
            "preferredName": primary_contact.preferredname,
            "phoneNumber": primary_contact.phone_number,
            "phoneCountryCode": primary_contact.phone_country_code,
            "extension": primary_contact.phone_extension,
            "faxNumber": primary_contact.fax_number,
            "emailAddress": primary_contact.email,
        }

    @classmethod
    def get_jurisdiction_from_application(
        cls, registration: Registration, applications: list | None = None
    ) -> Optional[str]:
        """Returns the jurisdiction of a registration."""
        if registration.rental_property.jurisdiction:
            return registration.rental_property.jurisdiction
        else:
            if applications is None:
                applications = Application.get_all_by_registration_id(registration.id)
            if applications:
                latest_application = sorted(applications, key=lambda app: app.application_date, reverse=True)[0]
                return (
                    latest_application.application_json.get("registration")
                    .get("strRequirements", {})
                    .get("organizationNm")
                )
        return None

    @classmethod
    def get_str_requirements_from_application(
        cls, registration: Registration, applications: list | None = None
    ) -> Optional[dict]:
        """Returns the strRequirements from the most recent application."""
        if applications is None:
            applications = Application.get_all_by_registration_id(registration.id)
        if not applications:
            return None

        latest_application = sorted(applications, key=lambda app: app.application_date, reverse=True)[0]
        return latest_application.application_json.get("registration", {}).get("strRequirements", {})
