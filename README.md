# fc-up42
UP42 Block for Fractional Cover calculation from Sentinel 2 L2A Data.
Applies the [JRSRP Fractional Cover Model](http://data.auscover.org.au/xwiki/bin/view/Product+pages/Landsat+Seasonal+Fractional+Cover)

## Steps to get this running

### Login to UP42 Registry
`docker login -u USERNAME registry.up42.com`

### Validate Manifest
`curl -X POST -H 'Content-Type: application/json' -d @UP42Manifest.json https://api.up42.com/validate-schema/block`

### Build Image
Use the "Push a block to the platform" option to get the following link

`docker build --build-arg manifest="$(cat UP42Manifest.json)" -t registry.up42.com/XXXXXXX-XXX-XXXXXXXXX-XXXXXXXX/fc-test:latest .`

### Push Image to the registry
`docker push registry.up42.com/XXXXXXX-XXX-XXXXXXXXX-XXXXXXXX/fc-test:latest`



