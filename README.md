[![Total alerts](https://img.shields.io/lgtm/alerts/g/Azure/sonic-platform-common.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Azure/sonic-platform-common/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/Azure/sonic-platform-common.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Azure/sonic-platform-common/context:python)

# SONiC: Software for Open Networking in the Cloud

## sonic-platform-common

Collection of Python packages which provide a common interface to platform-specific hardware peripherals in SONiC

## Cross-language transceiver API

`sonic_platform_api/facade.pyi` declares the shared API consumed by Rust
`xcvrd-rs`. `get_sfps(indices)` takes the physical indices from `port_config`
and reaches each slot through `ChassisBase.get_sfp(index)`. Rows carry that
`index` and an opaque `DeviceKey`; a change event's `device_id` names the same
physical index. Never subscript the returned rows with a physical port number:
vendors may start numbering at 0 or 1, and sparse inventories omit non-SFP
ports. `sfp_*` reads and actions address the row keys. Inventory does not read
EEPROM or consume latched flags.

The Rust trait uses `&self` and `Send + Sync`. Share one provider with `Arc`;
neither the provider nor its bridge needs to clone device state. Implementations
own cache synchronization and must not hold a device lock across an event wait.
The Python facade serializes per-slot operations, including decoder construction,
and invalidates decoders under the same lock after insert/remove events. Direct
reads resolve the current `get_xcvr_api()`; an unavailable decoder returns `None`
for optional scalars or JSON `null`, whereas a missing decoder method is
`NotSupported`.

Open-ended transceiver dictionaries cross as `Json` (JSON-encoded strings),
preserving vendor fields, nested values, nulls and non-finite readings as
`"-inf"`, `"inf"` and `"nan"`. This is a temporary untyped boundary: native
implementations must reproduce the Python dictionary schemas, and structural
comparison requires parsing rather than comparing wire strings. `DEFERRED_JSON`
in the declaration tracks each result's typed-schema follow-up; generation
rejects untracked or stale entries. Temperature is already `Optional[Celsius]`,
not JSON. `sfp_uses_legacy_pm` is the declared capability query for PM without
the newer VDM interface; it does not invoke either getter.

EEPROM operations use bytes and preserve read misses and failed writes. No
vendor base-class changes are required.

After editing the declaration, run `python3 generator/generate.py` and
`generator/check.sh` with the `testing` extra installed. The generator produces
the Python facade, Rust trait, PyO3 bridge and provider delegations. Daemons
depend on `platform-api` and `platform-provider`, and need the matching
`sonic_platform_api` Python package at runtime.

# Contribution guide

All contributors must sign a contribution license agreement (CLA) before contributions can be accepted. This process is now automated via a GitHub bot when submitting new pull request. If the contributor has not yet signed a CLA, the bot will create a comment on the pull request containing a link to electronically sign the CLA.

### GitHub Workflow

We're following basic GitHub Flow. If you have no idea what we're talking about, check out [GitHub's official guide](https://guides.github.com/introduction/flow/). Note that merge is only performed by the repository maintainer.

Guide for performing commits:

* Isolate each commit to one component/bugfix/issue/feature
* Use a standard commit message format:

>     [component/folder touched]: Description intent of your changes
> 
>     [List of changes]
>     
> 	  Signed-off-by: Your Name your@email.com
    
For example:

>     swss-common: Stabilize the ConsumerTable
>     
>     * Fixing autoreconf
>     * Fixing unit-tests by adding checkers and initialize the DB before start
>     * Adding the ability to select from multiple channels
>     * Health-Monitor - The idea of the patch is that if something went wrong with the notification channel, 
>       we will have the option to know about it (Query the LLEN table length).
>       
>       Signed-off-by: John Doe user@dev.null


* Each developer should fork this repository and [add the team as a Contributor](https://help.github.com/articles/adding-collaborators-to-a-personal-repository)
* Push your changes to your private fork and do "pull-request" to this repository
* Use a pull request to do code review
* Use issues to keep track of what is going on
